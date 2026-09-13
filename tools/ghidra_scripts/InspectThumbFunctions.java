// Disassemble selected Thumb functions and export listings and provisional pseudocode.
// Arguments: output text path, then one or more hexadecimal function entry addresses.
// @category Torneko

import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class InspectThumbFunctions extends GhidraScript {
    @Override
    protected void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException("Expected output path and function addresses");
        }
        StringBuilder output = new StringBuilder();
        DecompInterface decompiler = new DecompInterface();
        try {
            for (int i = 1; i < args.length; i++) {
                Address entry = toAddr(Long.decode(args[i]));
                if (getInstructionAt(entry) == null) {
                    currentProgram.getProgramContext().setValue(
                        currentProgram.getRegister("TMode"), entry, entry, BigInteger.ONE);
                } else if (!BigInteger.ONE.equals(currentProgram.getProgramContext().getValue(
                    currentProgram.getRegister("TMode"), entry, false))) {
                    throw new IllegalStateException("Existing instruction is not Thumb at " + entry);
                }
                if (!disassemble(entry) && getInstructionAt(entry) == null) {
                    throw new IllegalStateException("Could not disassemble " + entry);
                }
                Function function = getFunctionAt(entry);
                if (function == null) {
                    function = createFunction(entry, "text_probe_" + entry);
                }
                if (function == null) {
                    throw new IllegalStateException("Could not create function at " + entry);
                }
            }
            if (!decompiler.openProgram(currentProgram)) {
                throw new IllegalStateException(decompiler.getLastMessage());
            }
            for (int i = 1; i < args.length; i++) {
                Function function = getFunctionAt(toAddr(Long.decode(args[i])));
                output.append("\nFUNCTION ").append(function.getEntryPoint()).append('\n');
                InstructionIterator instructions = currentProgram.getListing().getInstructions(
                    function.getBody(), true);
                while (instructions.hasNext()) {
                    Instruction instruction = instructions.next();
                    output.append(instruction.getAddress()).append("  ")
                        .append(instruction).append('\n');
                }
                DecompileResults result = decompiler.decompileFunction(function, 30, monitor);
                if (result.decompileCompleted()) {
                    output.append("\nPROVISIONAL PSEUDOCODE\n")
                        .append(result.getDecompiledFunction().getC());
                } else {
                    output.append("\nDecompilation unavailable: ").append(result.getErrorMessage());
                }
            }
        } finally {
            decompiler.dispose();
        }
        Files.writeString(Path.of(args[0]), output.toString());
        println("TORNEKO_THUMB_INSPECTION_OK " + args[0]);
    }
}
