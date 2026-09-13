// Export occupied Thumb code ranges, preserving gaps as raw halfwords.
// Arguments: output path, then inclusive-start/exclusive-end hexadecimal pairs.
// @category Torneko
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;

public class InspectThumbRange extends GhidraScript {
    @Override protected void run() throws Exception {
        String[] args=getScriptArgs();
        if (args.length<3 || args.length%2!=1) throw new IllegalArgumentException("Expected output and start/end pairs");
        StringBuilder result=new StringBuilder();
        for(int i=1;i<args.length;i+=2) {
            long start=Long.decode(args[i]),end=Long.decode(args[i+1]);
            Address entry=toAddr(start);
            if (getInstructionAt(entry)==null) {
                currentProgram.getProgramContext().setValue(currentProgram.getRegister("TMode"),entry,entry,BigInteger.ONE);
            } else if (!BigInteger.ONE.equals(currentProgram.getProgramContext().getValue(
                    currentProgram.getRegister("TMode"),entry,false))) {
                throw new IllegalStateException("Existing instruction is not Thumb at "+entry);
            }
            disassemble(entry);
            result.append(String.format("RANGE %08x %08x (end exclusive)%n",start,end));
            for(long at=start;at<end;) {
                Address address=toAddr(at);Instruction instruction=getInstructionAt(address);
                if(instruction==null) {
                    result.append(String.format("%08x  .hword %04x ; data or undisassembled%n",at,getShort(address)&0xffff));at+=2;
                } else {
                    result.append(address).append("  ").append(instruction).append('\n');at+=instruction.getLength();
                }
            }
        }
        Files.writeString(Path.of(args[0]),result.toString());println("TORNEKO_THUMB_RANGES_OK "+args[0]);
    }
}
