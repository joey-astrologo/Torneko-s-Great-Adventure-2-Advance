// Verify the installed GBA loader and ARM disassembler on a temporary project.
// @category Torneko

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

public class VerifyGbaImport extends GhidraScript {
    @Override
    protected void run() throws Exception {
        Memory memory = currentProgram.getMemory();
        long[] regions = {0x02000000L, 0x03000000L, 0x04000000L,
                          0x05000000L, 0x06000000L, 0x07000000L, 0x08000000L};
        for (long region : regions) {
            MemoryBlock block = memory.getBlock(toAddr(region));
            if (block == null) {
                throw new IllegalStateException("Missing memory region: " + Long.toHexString(region));
            }
            println(block.getName() + " " + block.getStart() + " " + block.getSize());
        }
        if (!currentProgram.getLanguageID().toString().equals("ARM:LE:32:v4t")) {
            throw new IllegalStateException("Unexpected language: " + currentProgram.getLanguageID());
        }
        int branch = memory.getInt(toAddr(0x08000000L));
        if ((branch >>> 24) != 0xEA) {
            throw new IllegalStateException("Unexpected cartridge entry instruction");
        }
        int offset = branch & 0xFFFFFF;
        if ((offset & 0x800000) != 0) {
            offset -= 0x1000000;
        }
        Address entry = toAddr(0x08000008L + offset * 4L);
        if (!currentProgram.getSymbolTable().isExternalEntryPoint(entry)) {
            throw new IllegalStateException("Loader did not mark cartridge entry: " + entry);
        }
        disassemble(entry);
        if (getInstructionAt(entry) == null) {
            throw new IllegalStateException("Could not disassemble cartridge entry");
        }
        println("TORNEKO_GBA_IMPORT_OK entry=" + entry + " instruction=" + getInstructionAt(entry));
    }
}
