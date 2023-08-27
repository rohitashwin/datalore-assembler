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

SUPPORTED_REGISTERS = ['R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R6', RESERVED_REGISTER_NAME]
SUPPORTED_MULTI_INSTRUCTIONS = ['ADD', 'SUB', 'AND', 'XOR', 'ROL', 'ROR', 'LSL', 'LSR', 'MOV']
SUPPORTED_REGISTER_ONLY_INSTRUCTIONS = []
SUPPORTED_IMMEDIATE_ONLY_INSTRUCTIONS = []
SUPPORTED_MEMORY_INSTRUCTIONS = ['LDR', 'STR']
SUPPORTED_BRANCH_INSTRUCTIONS = ['BEQ']

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
	ADD R1, R2				// R1 = R1 + R2
    ADD R1, #37				// R1 = R1 + 37
SUB
	SUB R1, R2				// R1 = R1 - R2
    SUB R1, #37				// R1 = R1 - 37
AND
	AND R1, R2				// R1 = R1 & R2
    AND R1, #37				// R1 = R1 & 37
XOR
	XOR R1, R2				// R1 = R1 ^ R2
    XOR R1, #37				// R1 = R1 ^ 37
LDR
	LDR R1, #37				// R1 = MEM[37]
STR
	STR R1, #37				// MEM[37] = R1
ROL
	ROL R1, R2				// R1 = R1 rot<< R2
    ROL R1, #37				// R1 = R1 rot<< 37
ROR
	ROR R1, R2				// R1 = R1 rot>> R2
    ROR R1, #37				// R1 = R1 rot>> 37
LSL
	LSL R1, R2				// R1 = R1 << R2
    LSL R1, #37				// R1 = R1 << 37
LSR
	LSR R1, R2				// R1 = R1 >> R2
    LSR R1, #37				// R1 = R1 >> 37
BEQ
	BEQ R1, R2, <tag>		// if (R1 == R2) PC = R7
	BEQ R1, #37, <tag>		// if (R1 == 37) PC = R7
MOV
	MOV R1, R2				// R1 = R2
    MOV R1, #37				// R1 = 37

    
Tags are also supported:

@<tagname>: 

This will mark a tag. Make sure that the tag name is the only thing on the line. Tags are case sensitive. 
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
class SourceArtifact:
	pass
@dataclass
class RawInstruction(SourceArtifact):
	mnemonic: str
	operand1: str
	operand2: str
	tagname: str = None

@dataclass
class Tag(SourceArtifact):
	name: str

# maps tag names to line numbers
tag_map = dict()

# ----------------------------------------------
@dataclass
class IntermediateInstruction:
	mnemonic: str

@dataclass
class RegisterIntermediateInstruction(IntermediateInstruction):
	dest_reg: str
	src_reg: str

@dataclass
class ImmediateIntermediateInstruction(IntermediateInstruction):
	dest_reg: str
	imm: int

@dataclass
class MemoryIntermediateInstruction(IntermediateInstruction):
	is_load: bool
	dest_reg: str
	addr: int

@dataclass
class SetIntermediateInstruction(IntermediateInstruction):
	flag: bool = False
	imm: int

@dataclass
class BranchIntermediateInstruction(IntermediateInstruction):
	operand_reg1: str
	operand_reg2: str
	dest_addr: int

@dataclass
class TagIntermediateInstruction(IntermediateInstruction):
	tagname: str
# ----------------------------------------------

@dataclass
class MachineInstruction:
	mnemonic: str

@dataclass
class RegMachineInstr(MachineInstruction):
	dest_reg: str
	src_reg: str

@dataclass
class SetMachineInstr(MachineInstruction):
	flag: bool = False
	imm: int

@dataclass
class MemMachineInstr(MachineInstruction):
	is_load: bool
	dest_reg: str

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

def is_valid_instruction(tokens: [str]) -> bool:
	if len(tokens) != 3 or len(tokens) != 4 or tokens[0].startswith('@'):
		return False
	mnemonic = tokens[0]
	operand1 = tokens[1]
	operand2 = tokens[2]
	# multi instructions must either have two registers or one reg and one imm in the form of #<imm>
	if mnemonic in SUPPORTED_MULTI_INSTRUCTIONS:
		if operand1 in SUPPORTED_REGISTERS and operand2 in SUPPORTED_REGISTERS:
			return True
		elif operand1 in SUPPORTED_REGISTERS and operand2.startswith('#') and operand2[1:].isnumeric():
			return True
		else:
			return False
	elif mnemonic in SUPPORTED_REGISTER_ONLY_INSTRUCTIONS:
		if operand1 in SUPPORTED_REGISTERS and operand2 in SUPPORTED_REGISTERS:
			return True
		else:
			return False
	elif mnemonic in SUPPORTED_IMMEDIATE_ONLY_INSTRUCTIONS:
		if operand1 in SUPPORTED_REGISTERS and operand2.startswith('#') and operand2[1:].isnumeric():
			return True
		else:
			return False
	else:
		return False

def get_source_artifacts(cleaned_lines: [str]) -> [SourceArtifact]:
	source_artifacts = []
	for line in cleaned_lines:
		if line.startswith('@'):
			# tag
			tagname = line[1:]
			tag = Tag(name=tagname)
			source_artifacts.append(tag)
		else:
			# instruction (make sure mnemonic is upper case)
			tokens = line.split(' ')
			if is_valid_instruction(tokens):
				mnemonic = tokens[0]
				operand1 = tokens[1]
				operand2 = tokens[2]
				if len(tokens) == 4:
					tagname = tokens[3]
				else:
					tagname = None
				raw_instr = RawInstruction(mnemonic=mnemonic.upper(), operand1=operand1, operand2=operand2, tagname=tagname)
				source_artifacts.append(raw_instr)
			else:
				raise Exception(f'Invalid instruction: {line}')
	return source_artifacts

def get_intermediate_instructions(raw_instr: RawInstruction) -> [IntermediateInstruction]:
	intermediate_instructions = []
	mnemonic = raw_instr.mnemonic
	operand1 = raw_instr.operand1
	operand2 = raw_instr.operand2
	tagname = raw_instr.tagname
	if mnemonic in SUPPORTED_BRANCH_INSTRUCTIONS:
		# raise exception if tagname is not in tag_map
		if tagname not in tag_map:
			raise Exception(f'Invalid tag: {tagname}')
		branch_instr = BranchIntermediateInstruction(mnemonic=mnemonic, operand_reg1=operand1, operand_reg2=operand2, tagname=tagname)
		intermediate_instructions.append(branch_instr)
	elif mnemonic in SUPPORTED_MEMORY_INSTRUCTIONS:
		imm = int(operand2[1:])
		if mnemonic == 'LDR':
			intermediate_instructions.append(MemoryIntermediateInstruction(mnemonic=mnemonic, is_load=True, dest_reg=operand1, addr=imm))
		elif mnemonic == 'STR':
			intermediate_instructions.append(MemoryIntermediateInstruction(mnemonic=mnemonic, is_load=False, dest_reg=operand1, addr=imm))
	elif mnemonic in SUPPORTED_REGISTER_ONLY_INSTRUCTIONS:
		intermediate_instructions.append(RegisterIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, src_reg=operand2))
	elif mnemonic in SUPPORTED_IMMEDIATE_ONLY_INSTRUCTIONS:
		imm = int(operand2[1:])
		intermediate_instructions.append(ImmediateIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, imm=imm))
	elif mnemonic in SUPPORTED_MULTI_INSTRUCTIONS:
		if operand2.startswith('#'):
			imm = int(operand2[1:])
			intermediate_instructions.append(ImmediateIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, imm=imm))
		else:
			intermediate_instructions.append(RegisterIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, src_reg=operand2))
	else:
		raise Exception(f'Invalid instruction: {raw_instr}')
	
def process_source_artifacts(source_artifacts: [SourceArtifact]) -> [IntermediateInstruction]:
	machine_instructions = []
	for source_artifact in source_artifacts:
		if isinstance(source_artifact, RawInstruction):
			machine_instructions += get_intermediate_instructions(source_artifact)
		elif isinstance(source_artifact, Tag):
			machine_instructions.append(TagIntermediateInstruction(tagname=source_artifact.name))
	return machine_instructions