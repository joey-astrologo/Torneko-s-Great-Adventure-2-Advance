/* Research scheduler for the pinned mGBA 0.10.5 native SIO lockstep driver.
 * Cycle accounting follows src/platform/qt/MultiplayerController.cpp in that
 * source tree (Mozilla Public License 2.0). No cartridge or core code is patched.
 * Both cores run on one host thread; the driver owns serial data and interrupts.
 */
#include <mgba/core/core.h>
#include <mgba/debugger/debugger.h>
#include <mgba/internal/arm/arm.h>
#include <mgba/internal/gba/gba.h>
#include <mgba/internal/gba/sio/lockstep.h>
#include <stdlib.h>

#define WIRE_CAPACITY 16384
struct Pair {
    struct GBASIOLockstep link;
    struct GBASIOLockstepNode nodes[2];
    int awake[2], cycles[2];
    unsigned waitMask;
    uint64_t started, finished, slaveFinished;
    uint16_t words[WIRE_CAPACITY][2];
};
static struct Pair* pair(struct mLockstep* s) { return s->context; }
static bool signal_peer(struct mLockstep* s, unsigned mask) {
    struct Pair* p = pair(s);
    p->waitMask &= ~mask;
    bool woke = !p->waitMask && !p->awake[0];
    if (woke) p->awake[0] = 1;
    return woke;
}
static bool wait_peer(struct mLockstep* s, unsigned mask) {
    struct Pair* p = pair(s);
    p->waitMask |= mask;
    bool slept = p->awake[0];
    p->awake[0] = 0;
    if (s->transferActive == TRANSFER_STARTED) ++p->started;
    if (s->transferActive == TRANSFER_FINISHED) {
        if (p->finished < WIRE_CAPACITY) {
            p->words[p->finished][0] = p->link.multiRecv[0];
            p->words[p->finished][1] = p->link.multiRecv[1];
        }
        ++p->finished;
    }
    return slept;
}
static void add_cycles(struct mLockstep* s, int id, int32_t cycles) {
    struct Pair* p = pair(s);
    if (cycles < 0) abort();
    if (!id) {
        if (p->nodes[1].d.p->mode > SIO_MULTI) return;
        p->cycles[1] += cycles;
        if (!p->awake[1]) p->nodes[1].nextEvent += p->cycles[1];
        p->awake[1] = 1;
    } else p->cycles[id] += cycles;
}
static int32_t use_cycles(struct mLockstep* s, int id, int32_t cycles) {
    struct Pair* p = pair(s);
    if (s->transferActive == TRANSFER_FINISHED && p->nodes[id].transferFinished)
        ++p->slaveFinished;
    p->cycles[id] -= cycles;
    if (p->cycles[id] <= 0) p->awake[id] = 0;
    return p->cycles[id];
}
static int32_t unused_cycles(struct mLockstep* s, int id) { return pair(s)->cycles[id]; }
static void unload(struct mLockstep* s, int id) {
    struct Pair* p = pair(s);
    if (id) {
        p->cycles[id] = 0;
        signal_peer(s, 1U << id);
        p->awake[id] = 1;
    } else {
        p->cycles[1] += p->nodes[0].eventDiff;
        if (!p->awake[1]) p->nodes[1].nextEvent += p->cycles[1];
        p->awake[1] = 1;
    }
}
size_t pair_gba_size(void) { return sizeof(struct GBA); }
void* pair_create(struct GBASIO* sio0, struct GBASIO* sio1) {
    struct Pair* p = calloc(1, sizeof(*p));
    if (!p) return NULL;
    mLockstepInit(&p->link.d);
    GBASIOLockstepInit(&p->link);
    p->link.d.context = p;
    p->link.d.signal = signal_peer;
    p->link.d.wait = wait_peer;
    p->link.d.addCycles = add_cycles;
    p->link.d.useCycles = use_cycles;
    p->link.d.unusedCycles = unused_cycles;
    p->link.d.unload = unload;
    struct GBASIO* ports[2] = {sio0, sio1};
    for (int i = 0; i < 2; ++i) {
        p->awake[i] = 1;
        GBASIOLockstepNodeCreate(&p->nodes[i]);
        if (!GBASIOLockstepAttachNode(&p->link, &p->nodes[i])) abort();
        GBASIOSetDriver(ports[i], &p->nodes[i].d, SIO_MULTI);
    }
    return p;
}
static void pair_step(struct Pair* p, int id, struct mDebugger* d) {
    if (d->state != DEBUGGER_RUNNING) { mDebuggerRun(d); return; }
    struct ARMCore* cpu = d->core->cpu;
    /* ARMRun's halted-event loop ignores the caller's lockstep wait. Drain
     * events here, yielding immediately when the original driver blocks this
     * core. Once cycles < nextEvent, mDebuggerRun performs one normal native
     * instruction and its normal breakpoint check. This preserves every game
     * instruction, serial register, transferred word and interrupt. */
    while (cpu->cycles >= cpu->nextEvent) {
        cpu->irqh.processEvents(cpu);
        if (!p->awake[id]) return;
    }
    mDebuggerRun(d);
}
void pair_pump(void* v, struct mDebugger* d0, struct mDebugger* d1) {
    struct Pair* p = v;
    for (int n = 0; n < 2048; ++n) {
        if (p->awake[0]) pair_step(p, 0, d0);
        if (p->awake[1]) pair_step(p, 1, d1);
        if (!p->awake[0] && !p->awake[1]) break;
    }
}
int pair_awake(void* v, int id) { return ((struct Pair*)v)->awake[id]; }
uint64_t pair_count(void* v, int which) {
    struct Pair* p = v;
    return which == 0 ? p->started : which == 1 ? p->finished : p->slaveFinished;
}
void pair_words(void* v, uint16_t* out) {
    struct Pair* p = v;
    for (unsigned i = 0; i < p->finished && i < WIRE_CAPACITY; ++i) {
        out[2*i] = p->words[i][0]; out[2*i+1] = p->words[i][1];
    }
}
void pair_destroy(void* v) {
    struct Pair* p = v;
    for (int i = 1; i >= 0; --i) {
        GBASIOSetDriver(p->nodes[i].d.p, NULL, SIO_MULTI);
        GBASIOLockstepDetachNode(&p->link, &p->nodes[i]);
    }
    mLockstepDeinit(&p->link.d);
    free(p);
}
