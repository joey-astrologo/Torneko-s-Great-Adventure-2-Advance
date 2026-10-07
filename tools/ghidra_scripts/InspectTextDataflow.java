// Export decompiler SSA operations for explicitly selected Thumb functions.
// This is research evidence; unresolved branches and parameters stay explicit.
// @category Torneko

import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Iterator;
import java.util.LinkedHashMap;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.Function;
import ghidra.program.model.pcode.HighParam;
import ghidra.program.model.pcode.PcodeOp;
import ghidra.program.model.pcode.PcodeOpAST;
import ghidra.program.model.pcode.Varnode;

public class InspectTextDataflow extends GhidraScript {
    private String key(Varnode node) {
        if (node == null) return "-";
        if (node.isConstant()) return "constant:" + Long.toHexString(node.getOffset()) + ":" + node.getSize();
        PcodeOp def = node.getDef();
        if (def != null) return "value:" + def.getSeqnum().getTarget() + ":" + def.getSeqnum().getTime();
        return "input:" + node.getAddress() + ":" + node.getSize();
    }

    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) throw new IllegalArgumentException("Expected output and function entries");
        for (int i = 1; i < args.length; i++) {
            Address entry = toAddr(Long.decode(args[i]));
            if (getInstructionAt(entry) == null) {
                currentProgram.getProgramContext().setValue(
                    currentProgram.getRegister("TMode"), entry, entry, BigInteger.ONE);
            } else if (!BigInteger.ONE.equals(currentProgram.getProgramContext().getValue(
                currentProgram.getRegister("TMode"), entry, false))) {
                throw new IllegalStateException("Existing instruction is not Thumb at " + entry);
            }
            if (!disassemble(entry) && getInstructionAt(entry) == null)
                throw new IllegalStateException("Cannot disassemble " + entry);
            if (getFunctionAt(entry) == null && createFunction(entry, "text_flow_" + entry) == null)
                throw new IllegalStateException("Cannot create " + entry);
        }
        DecompInterface decompiler = new DecompInterface();
        StringBuilder output = new StringBuilder();
        try {
            if (!decompiler.openProgram(currentProgram)) throw new IllegalStateException(decompiler.getLastMessage());
            for (int i = 1; i < args.length; i++) {
                Function function = getFunctionAt(toAddr(Long.decode(args[i])));
                DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
                if (!result.decompileCompleted()) throw new IllegalStateException(result.getErrorMessage());
                output.append("FUNCTION\t").append(function.getEntryPoint()).append('\n');
                LinkedHashMap<String, Varnode> nodes = new LinkedHashMap<>();
                StringBuilder operations = new StringBuilder();
                Iterator<PcodeOpAST> iterator = result.getHighFunction().getPcodeOps();
                while (iterator.hasNext()) {
                    PcodeOpAST op = iterator.next();
                    operations.append("OP\t").append(op.getSeqnum().getTarget()).append('\t')
                        .append(op.getSeqnum().getTime()).append('\t').append(op.getMnemonic())
                        .append('\t').append(key(op.getOutput()));
                    if (op.getOutput() != null) nodes.put(key(op.getOutput()), op.getOutput());
                    for (int j = 0; j < op.getNumInputs(); j++) {
                        Varnode node = op.getInput(j);
                        nodes.put(key(node), node);
                        operations.append('\t').append(key(node));
                    }
                    operations.append('\n');
                }
                for (String id : nodes.keySet()) {
                    Varnode node = nodes.get(id);
                    Register register = node.isRegister() ? currentProgram.getRegister(node.getAddress(), node.getSize()) : null;
                    int parameter = node.getHigh() instanceof HighParam ? ((HighParam) node.getHigh()).getSlot() : -1;
                    output.append("NODE\t").append(id).append('\t').append(node.getSize())
                        .append('\t').append(node.isConstant() ? Long.toUnsignedString(node.getOffset()) : "-")
                        .append('\t').append(register == null ? "-" : register.getName())
                        .append('\t').append(parameter).append('\t').append(node.getAddress()).append('\n');
                }
                output.append(operations).append("END\n");
            }
        } finally { decompiler.dispose(); }
        Files.writeString(Path.of(args[0]), output.toString());
        println("TORNEKO_TEXT_DATAFLOW_OK " + args[0]);
    }
}
