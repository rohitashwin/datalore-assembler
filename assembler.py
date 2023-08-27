from dataclasses import dataclass

SOURCE_FILE = 'source.dlas'

MEM_OPCODE = '000'
ADD_OPCODE = '001'
AND_OPCODE = '010'
XOR_OPCODE = '011'
ROL_OPCODE = '100'
BEQ_OPCODE = '101'
SET_OPCODE = '110'
MOV_OPCODE = '111'

RESERVED_REGISTER_NAME = 'R7'
'''
Machine Code (9 Bits):

General Layout:
[8:6] Opcode
[5:3] Destination Register
[2:0] Source Register
'''

'''
Supported Instructions:

ADD
	ADD R1, R2		// R1 = R1 + R2
    ADD R1, #37		// R1 = R1 + 37
SUB
	SUB R1, R2		// R1 = R1 - R2
    SUB R1, #37		// R1 = R1 - 37
AND
	AND R1, R2		// R1 = R1 & R2
    AND R1, #37		// R1 = R1 & 37
XOR
	XOR R1, R2		// R1 = R1 ^ R2
    XOR R1, #37		// R1 = R1 ^ 37
LDR
	LDR R1, #37		// R1 = MEM[37]
STR
	STR R1, #37		// MEM[37] = R1
ROL
	ROL R1, R2		// R1 = R1 rot<< R2
    ROL R1, #37		// R1 = R1 rot<< 37
ROR
	ROR R1, R2		// R1 = R1 rot>> R2
    ROR R1, #37		// R1 = R1 rot>> 37
LSL
	LSL R1, R2		// R1 = R1 << R2
    LSL R1, #37		// R1 = R1 << 37
LSR
	LSR R1, R2		// R1 = R1 >> R2
    LSR R1, #37		// R1 = R1 >> 37
BEQ
	BEQ R1, R2		// if (R1 == R2) PC = R7
	BEQ R1, #37		// if (R1 == 37) PC = R7
MOV
	MOV R1, R2		// R1 = R2
    MOV R1, #37		// R1 = 37
    
How are immediates handled?

R7 is reserved for storing immediate values. The machine itself does not support immediates directly - everything has to be put into 
R7 first. This is done by the assembler. The assembler will take the immediate value and store it in R7. Then, the assembler will call the same 
instruction again, but with R7 as the source register. This will cause the machine to perform the operation with the immediate value in R7.

The only instruction that can actually use R7 is the SET instruction. This instruction is not accessible to the programmer. It is only used 
by the assembler to set the value of R7. 

SET Usage Guide (Assembler Only):

Since the registers are 8 bits wide but we only have 6 bits remaining after the opcode, we can need to call SET twice in order to fully set R7.

Bit Layout: [8:6] 	Opcode (110 for SET)
			[5]		Unused
			[4]		Flag (0 for setting the lower 4 bits, 1 for setting the upper 4 bits)
			[3:0]	Half of the immediate value

'''

@dataclass
class ProgrammerInstruction:
	is_src_imm: bool = False
	mnemonic: str
	dest: str
	src: str = None

@dataclass
class MachineInstruction:
	opcode: str
	dest: str
	src: str

def clean_lines(lines: [str]) -> [str]:
	cleaned = []
	# trim the lines
	# remove empty lines
	# remove lines that start with //
	for line in lines:
		line = line.strip()
		if line != '' and not line.startswith('//'):
			cleaned.append(line)
	return cleaned

def get_lines(filename: str) -> [str]:
	with open(filename) as f:
		lines = f.readlines()
	return lines

def get_cleaned_lines(filename: str) -> [str]:
	lines = get_lines(filename)
	return clean_lines(lines)

def get_tokens(line: str) -> [str]:
	line = line.replace(',', ' ')
	tokens = [token.strip() for token in line.split(' ')]
	return tokens	