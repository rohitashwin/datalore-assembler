from dataclasses import dataclass
from util import *
import argparse

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
SUPPORTED_SINGLE_INSTRUCTIONS = ['ZER']

'''
Machine Code (9 Bits):

General Layout:
[8:6] Opcode
[5:3] Destination Register
[2:0] Source Register
'''

'''
Programmer Supported Instructions:

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
	LDR R1, R2
	LDR R1, #37				// R1 = MEM[37]
STR
	STR R1, R2
	STR R1, #37				// MEM[37] = R1
ROL
	ROL R1, R2				// R1 = R1 rot<< R2
    ROL R1, #37				// R1 = R1 rot<< 37
ROR
    ROR R1, #37				// R1 = R1 rot>> 37
LSL
    LSL R1, #37				// R1 = R1 << 37
LSR
    LSR R1, #37				// R1 = R1 >> 37
BEQ
	BEQ R1, R2, <tag>		// if (R1 == R2) PC = R7
MOV
	MOV R1, R2				// R1 = R2
    MOV R1, #37				// R1 = 37
ZER
	ZER R1					// R1 = 0

    
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

'''
Machine Supported Instructions:
(Bit Layout - 9 Bits)

MEM
	000 OPCODE
	RRR TARGET REGISTER
	F 	FLAG (0 for load, 1 for store)
	XX	UNUSED	

ADD
	001 OPCODE
	RRR DEST REGISTER
	RRR SOURCE REGISTER

AND
	010 OPCODE
	RRR DEST REGISTER
	RRR SOURCE REGISTER

XOR
	011 OPCODE
	RRR DEST REGISTER
	RRR SOURCE REGISTER

ROL
	100 OPCODE
	RRR DEST REGISTER
	RRR SOURCE REGISTER

BEQ
	101 OPCODE
	RRR OPERAND REGISTER 1
	RRR OPERAND REGISTER 2

SET
	110 	OPCODE
	X		UNUSED
	F		FLAG (0 for setting the lower 4 bits, 1 for setting the upper 4 bits)
	XXXX 	HALF IMMEDIATE

MOV
	111 OPCODE
	RRR DEST REGISTER
	RRR SOURCE REGISTER

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
	imm: str

@dataclass
class MemoryIntermediateInstruction(IntermediateInstruction):
	is_load: bool
	target_reg: str
	source_reg: str
	addr: str

@dataclass
class BranchIntermediateInstruction(IntermediateInstruction):
	operand_reg1: str
	operand_reg2: str
	tagname: str

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
	flag: bool
	imm: str

@dataclass
class MemMachineInstr(MachineInstruction):
	is_load: bool
	target_reg: str
	target_location: str

@dataclass
class BrnMachineInstr(MachineInstruction):
	operand_reg1: str
	operand_reg2: str
	tagname: str

@dataclass
class TagMachineInstruction(MachineInstruction):
	tagname: str

# ----------------------------------------------

def is_valid_instruction(tokens: [str]) -> bool:
	if len(tokens) != 2 and len(tokens) != 3 and len(tokens) != 4 and not tokens[0].startswith('@'):
		return False
	mnemonic = tokens[0]
	operand1 = tokens[1]
	operand2 = None
	if len(tokens) == 3 or len(tokens) == 4:
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
	elif mnemonic in SUPPORTED_MEMORY_INSTRUCTIONS:
		if operand1 in SUPPORTED_REGISTERS and operand2 in SUPPORTED_REGISTERS:
			return True
		elif operand1 in SUPPORTED_REGISTERS and operand2.startswith('#') and operand2[1:].isnumeric():
			return True
		else:
			return False
	elif mnemonic in SUPPORTED_BRANCH_INSTRUCTIONS:
		if operand1 in SUPPORTED_REGISTERS and operand2 in SUPPORTED_REGISTERS and len(tokens) == 4:
			return True
		else:
			return False
	elif mnemonic in SUPPORTED_SINGLE_INSTRUCTIONS:
		if operand1 in SUPPORTED_REGISTERS and len(tokens) == 2:
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
			tokens = line.replace(',', '').split(' ')
			if is_valid_instruction(tokens):
				mnemonic = tokens[0].upper()
				operand1 = tokens[1]
				operand2 = None
				tagname = None
				if len(tokens) == 3:
					operand2 = tokens[2]
				elif len(tokens) == 4:
					operand2 = tokens[2]
					tagname = tokens[3]
				raw_instr = RawInstruction(mnemonic=mnemonic, operand1=operand1, operand2=operand2, tagname=tagname)
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
		branch_instr = BranchIntermediateInstruction(mnemonic=mnemonic, operand_reg1=operand1, operand_reg2=operand2, tagname=tagname)
		intermediate_instructions.append(branch_instr)
	elif mnemonic in SUPPORTED_MEMORY_INSTRUCTIONS:
		is_load = mnemonic == 'LDR'
		if operand2.startswith('#'):
			mem_instr = MemoryIntermediateInstruction(mnemonic=mnemonic, is_load=is_load, target_reg=operand1, source_reg=None, addr=operand2[1:])
		else:
			mem_instr = MemoryIntermediateInstruction(mnemonic=mnemonic, is_load=is_load, target_reg=operand1, source_reg=operand2, addr=None)
		intermediate_instructions.append(mem_instr)
	elif mnemonic in SUPPORTED_REGISTER_ONLY_INSTRUCTIONS:
		intermediate_instructions.append(RegisterIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, src_reg=operand2))
	elif mnemonic in SUPPORTED_IMMEDIATE_ONLY_INSTRUCTIONS:
		imm = operand2[1:]
		intermediate_instructions.append(ImmediateIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, imm=imm))
	elif mnemonic in SUPPORTED_MULTI_INSTRUCTIONS:
		if operand2.startswith('#'):
			imm = operand2[1:]
			intermediate_instructions.append(ImmediateIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, imm=imm))
		else:
			intermediate_instructions.append(RegisterIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, src_reg=operand2))
	elif mnemonic in SUPPORTED_SINGLE_INSTRUCTIONS:
		intermediate_instructions.append(RegisterIntermediateInstruction(mnemonic=mnemonic, dest_reg=operand1, src_reg=None))
	else:
		raise Exception(f'Invalid instruction: {raw_instr}')
	return intermediate_instructions
	
def process_source_artifacts(source_artifacts: [SourceArtifact]) -> [IntermediateInstruction]:
	intermediate_instructions = []
	for source_artifact in source_artifacts:
		if isinstance(source_artifact, RawInstruction):
			intermediate_instructions += get_intermediate_instructions(source_artifact)
		elif isinstance(source_artifact, Tag):
			intermediate_instructions.append(TagIntermediateInstruction(mnemonic=None, tagname=source_artifact.name))
	return intermediate_instructions

def process_general_register_instruction(reg_instr: RegisterIntermediateInstruction) -> [MachineInstruction]:
	return [RegMachineInstr(mnemonic=reg_instr.mnemonic, dest_reg=reg_instr.dest_reg, src_reg=reg_instr.src_reg)]

def process_general_immediate_instruction(imm_instr: ImmediateIntermediateInstruction) -> [MachineInstruction]:
	print(imm_instr.imm)
	left_imm, right_imm = get_half_imms(imm_instr.imm)
	first_set_instr = SetMachineInstr(mnemonic='SET', flag=False, imm=left_imm)
	second_set_instr = SetMachineInstr(mnemonic='SET', flag=True, imm=right_imm)
	reg_instr = RegMachineInstr(mnemonic=imm_instr.mnemonic, dest_reg=imm_instr.dest_reg, src_reg=RESERVED_REGISTER_NAME)
	return [first_set_instr, second_set_instr, reg_instr]

def process_add_instr(add_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(add_instr, RegisterIntermediateInstruction):
		return process_general_register_instruction(add_instr)
	elif isinstance(add_instr, ImmediateIntermediateInstruction):
		return process_general_immediate_instruction(add_instr)
	else:
		raise Exception(f'Invalid ADD Instruction: {add_instr}')

def process_sub_instr(sub_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(sub_instr, RegisterIntermediateInstruction):
		raise Exception(f'SUB instruction does not support register operands')
	elif isinstance(sub_instr, ImmediateIntermediateInstruction):
		# convert sub into add and 2s complement the immediate value
		sub_instr.mnemonic = 'ADD'
		# 2s complement the immediate value
		imm = get_twos_complement_negative(sub_instr.imm)
		left_half_imm, right_half_imm = imm[:4], imm[4:]
		first_set_instr = SetMachineInstr(mnemonic='SET', flag=False, imm=left_half_imm)
		second_set_instr = SetMachineInstr(mnemonic='SET', flag=True, imm=right_half_imm)
		reg_instr = RegMachineInstr(mnemonic='ADD', dest_reg=sub_instr.dest_reg, src_reg=RESERVED_REGISTER_NAME)
		return [first_set_instr, second_set_instr, reg_instr]
	else:
		raise Exception(f'Invalid SUB Instruction: {sub_instr}')

def process_and_instr(and_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(and_instr, RegisterIntermediateInstruction):
		return process_general_register_instruction(and_instr)
	elif isinstance(and_instr, ImmediateIntermediateInstruction):
		return process_general_immediate_instruction(and_instr)
	else:
		raise Exception(f'Invalid AND Instruction: {and_instr}')

def process_mem_instruction(mem_instr: MemoryIntermediateInstruction) -> [MachineInstruction]:
	if mem_instr.source_reg is None and mem_instr.addr is not None:
		addr = int(mem_instr.addr)
		left_half_addr, right_half_addr = get_half_imms(addr)
		first_set_instr = SetMachineInstr(mnemonic='SET', flag=False, imm=left_half_addr)
		second_set_instr = SetMachineInstr(mnemonic='SET', flag=True, imm=right_half_addr)
		mem_instr = MemMachineInstr(mnemonic='MEM', is_load=mem_instr.is_load, target_reg=mem_instr.target_reg, target_location=RESERVED_REGISTER_NAME)
		return [first_set_instr, second_set_instr, mem_instr]
	elif mem_instr.source_reg is not None and mem_instr.addr is None:
		mov_instr = RegMachineInstr(mnemonic='MOV', dest_reg=RESERVED_REGISTER_NAME, src_reg=mem_instr.source_reg)
		mem_instr = MemMachineInstr(mnemonic='MEM', is_load=mem_instr.is_load, target_reg=mem_instr.target_reg, target_location=RESERVED_REGISTER_NAME)
		return [mov_instr, mem_instr]
	else:
		raise Exception(f'Invalid State detected in Mem instruction: {mem_instr}')

def process_xor_instr(xor_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(xor_instr, RegisterIntermediateInstruction):
		return process_general_register_instruction(xor_instr)
	elif isinstance(xor_instr, ImmediateIntermediateInstruction):
		return process_general_immediate_instruction(xor_instr)
	else:
		raise Exception(f'Invalid XOR Instruction: {xor_instr}')

def process_rol_instr(rol_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(rol_instr, RegisterIntermediateInstruction):
		return process_general_register_instruction(rol_instr)
	elif isinstance(rol_instr, ImmediateIntermediateInstruction):
		return process_general_immediate_instruction(rol_instr)
	else:
		raise Exception(f'Invalid ROL Instruction: {rol_instr}')

def process_ror_instr(ror_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(ror_instr, RegisterIntermediateInstruction):
		raise Exception(f'ROR instruction does not support register operands')
	elif isinstance(ror_instr, ImmediateIntermediateInstruction):
		shamt = int(ror_instr.imm)
		shamt = shamt % 8
		shamt = 8 - shamt
		ror_instr.imm = str(shamt)
		ror_instr.mnemonic = 'ROL'
		return process_general_immediate_instruction(ror_instr)
	else:
		raise Exception(f'Invalid ROR Instruction: {ror_instr}')

def process_lsl_instr(lsl_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(lsl_instr, RegisterIntermediateInstruction):
		raise Exception(f'LSL instruction does not support register operands')
	elif isinstance(lsl_instr, ImmediateIntermediateInstruction):
		shamt = int(lsl_instr.imm)
		if shamt >= 8:
			return [RegMachineInstr(mnemonic='XOR', dest_reg=lsl_instr.dest_reg, src_reg=lsl_instr.dest_reg)]
		else:
			shift_amt = int(lsl_instr.imm)
			left_half_imm, right_half_imm = get_half_imms(shift_amt)
			first_set_instr_rol = SetMachineInstr(mnemonic='SET', flag=False, imm=left_half_imm)
			second_set_instr_rol = SetMachineInstr(mnemonic='SET', flag=True, imm=right_half_imm)
			reg_instr = RegMachineInstr(mnemonic='ROL', dest_reg=lsl_instr.dest_reg, src_reg=RESERVED_REGISTER_NAME)
			mask = get_mask_bits_rtl(shamt)
			left_half_mask, right_half_mask = mask[:4], mask[4:]
			first_set_instr_mask = SetMachineInstr(mnemonic='SET', flag=False, imm=left_half_mask)
			second_set_instr_mask = SetMachineInstr(mnemonic='SET', flag=True, imm=right_half_mask)
			mask_instr = RegMachineInstr(mnemonic='AND', dest_reg=lsl_instr.dest_reg, src_reg=RESERVED_REGISTER_NAME)
			return [first_set_instr_rol, second_set_instr_rol, reg_instr, first_set_instr_mask, second_set_instr_mask, mask_instr]
	else:
		raise Exception(f'Invalid LSL Instruction: {lsl_instr}')

def process_lsr_instr(lsr_instr: IntermediateInstruction) -> [MachineInstruction]:
	# ROL is the only available rotate instruction
	if isinstance(lsr_instr, RegisterIntermediateInstruction):
		raise Exception(f'LSR instruction does not support register operands')
	elif isinstance(lsr_instr, ImmediateIntermediateInstruction):
		shamt = int(lsr_instr.imm)
		if shamt >= 8:
			return [RegMachineInstr(mnemonic='XOR', dest_reg=lsr_instr.dest_reg, src_reg=lsr_instr.dest_reg)]
		else:
			shift_amt = int(lsr_instr.imm)
			shift_amt = 8 - shift_amt
			left_half_imm, right_half_imm = get_half_imms(shift_amt)
			first_set_instr_rol = SetMachineInstr(mnemonic='SET', flag=False, imm=left_half_imm)
			second_set_instr_rol = SetMachineInstr(mnemonic='SET', flag=True, imm=right_half_imm)
			reg_instr = RegMachineInstr(mnemonic='ROL', dest_reg=lsr_instr.dest_reg, src_reg=RESERVED_REGISTER_NAME)
			mask = get_mask_bits_rtl(shamt)
			mask = mask[::-1]
			left_half_mask, right_half_mask = mask[:4], mask[4:]
			first_set_instr_mask = SetMachineInstr(mnemonic='SET', flag=False, imm=left_half_mask)
			second_set_instr_mask = SetMachineInstr(mnemonic='SET', flag=True, imm=right_half_mask)
			mask_instr = RegMachineInstr(mnemonic='AND', dest_reg=lsr_instr.dest_reg, src_reg=RESERVED_REGISTER_NAME)
			return [first_set_instr_rol, second_set_instr_rol, reg_instr, first_set_instr_mask, second_set_instr_mask, mask_instr]

def process_zer_instr(zer_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(zer_instr, RegisterIntermediateInstruction):
		return [RegMachineInstr(mnemonic='XOR', dest_reg=zer_instr.dest_reg, src_reg=zer_instr.dest_reg)]
	else:
		raise Exception(f'Invalid ZER Instruction: {zer_instr}')

def process_beq_instr(beq_instr: BranchIntermediateInstruction) -> [MachineInstruction]:
	if beq_instr.operand_reg2.startswith('#'):
		raise Exception(f'BEQ instruction does not support immediate operands')
	else:
		# Store instruction
		# data_mem[200]: XXXX 1234 
		# data_mem[201]: 5678 9ABC
		# First Set: 	1234
		# Second Set: 	5678
		# Third Set: 	9ABC

		instruction_group = [
			SetMachineInstr(mnemonic='SET', flag=True, imm=None),														# First Set for Right Half data_mem[200]
			MemMachineInstr(mnemonic='MEM', is_load=False, target_reg=RESERVED_REGISTER_NAME, target_location='200'),	# Set the memory instruction
			SetMachineInstr(mnemonic='SET', flag=False, imm=None),														# Second Set for Left Half data_mem[201]
			SetMachineInstr(mnemonic='SET', flag=True, imm=None),														# Third Set for Right Hald data_mem[201]
			MemMachineInstr(mnemonic='MEM', is_load=False, target_reg=RESERVED_REGISTER_NAME, target_location='201'),	# Set the memory instruction
			BrnMachineInstr(mnemonic='BEQ', operand_reg1=beq_instr.operand_reg1, operand_reg2=beq_instr.operand_reg2, tagname=beq_instr.tagname)
		]
		return instruction_group

def process_mov_instr(mov_instr: IntermediateInstruction) -> [MachineInstruction]:
	if isinstance(mov_instr, RegisterIntermediateInstruction):
		return process_general_register_instruction(mov_instr)
	elif isinstance(mov_instr, ImmediateIntermediateInstruction):
		return process_general_immediate_instruction(mov_instr)
	else:
		raise Exception(f'Invalid MOV Instruction: {mov_instr}')

def process_tag_instr(tag_instr: TagIntermediateInstruction) -> [MachineInstruction]:
	# remove the last character from the tag name
	tagname = tag_instr.tagname.strip(':')
	return [TagMachineInstruction(mnemonic=None, tagname=tagname)]

def process_intermediate_instruction(intermediate_instr: IntermediateInstruction) -> [MachineInstruction]:
	mnemonic = intermediate_instr.mnemonic
	if isinstance(intermediate_instr, TagIntermediateInstruction):
		return process_tag_instr(intermediate_instr)
	if mnemonic == 'ADD':
		return process_add_instr(intermediate_instr)
	elif mnemonic == 'SUB':
		return process_sub_instr(intermediate_instr)
	elif mnemonic == 'AND':
		return process_and_instr(intermediate_instr)
	elif mnemonic == 'LDR' or mnemonic == 'STR':
		return process_mem_instruction(intermediate_instr)
	elif mnemonic == 'XOR':
		return process_xor_instr(intermediate_instr)
	elif mnemonic == 'ROL':
		return process_rol_instr(intermediate_instr)
	elif mnemonic == 'ROR':
		return process_ror_instr(intermediate_instr)
	elif mnemonic == 'LSL':
		return process_lsl_instr(intermediate_instr)
	elif mnemonic == 'LSR':
		return process_lsr_instr(intermediate_instr)
	elif mnemonic == 'BEQ':
		return process_beq_instr(intermediate_instr)
	elif mnemonic == 'MOV':
		return process_mov_instr(intermediate_instr)
	elif mnemonic == 'ZER':
		return process_zer_instr(intermediate_instr)
	else:
		raise Exception(f'Invalid intermediate instruction: {intermediate_instr}')

def process_intermediate_instructions(intermediate_instructions: [IntermediateInstruction]) -> [MachineInstruction]:
	machine_instructions = []
	for intermediate_instr in intermediate_instructions:
		machine_instructions += process_intermediate_instruction(intermediate_instr)
	return machine_instructions

def get_register_bits(reg: str) -> str:
	if reg == 'R0':
		return '000'
	elif reg == 'R1':
		return '001'
	elif reg == 'R2':
		return '010'
	elif reg == 'R3':
		return '011'
	elif reg == 'R4':
		return '100'
	elif reg == 'R5':
		return '101'
	elif reg == 'R6':
		return '110'
	elif reg == 'R7':
		return '111'
	else:
		raise Exception(f'Invalid register: {reg}')
	
def get_opcode_bits(mnemonic: str) -> str:
	if mnemonic == 'ADD':
		return ADD_OPCODE
	elif mnemonic == 'AND':
		return AND_OPCODE
	elif mnemonic == 'XOR':
		return XOR_OPCODE
	elif mnemonic == 'ROL':
		return ROL_OPCODE
	elif mnemonic == 'BEQ':
		return BEQ_OPCODE
	elif mnemonic == 'SET':
		return SET_OPCODE
	elif mnemonic == 'MEM':
		return MEM_OPCODE
	elif mnemonic == 'MOV':
		return MOV_OPCODE
	else:
		raise Exception(f'Invalid mnemonic: {mnemonic}')

'''
Returns the tagless version of the machine instructions with all the tag information being extracted
'''
def extract_tag_information(machine_instructions: [MachineInstruction]) -> [MachineInstruction]:
	ctr = 0
	for machine_instr in machine_instructions:
		if isinstance(machine_instr, TagMachineInstruction):
			tag_map[machine_instr.tagname] = ctr
			machine_instructions.remove(machine_instr)
		else:
			ctr += 1
	return machine_instructions

def tag_branch_instructions(machine_instructions: [MachineInstruction]) -> [MachineInstruction]:
	# store the binary representation of the offset from the current instruction to the tag
	for i, machine_instr in enumerate(machine_instructions):
		if isinstance(machine_instr, BrnMachineInstr):
			tagname = machine_instr.tagname
			if tagname not in tag_map:
				raise Exception(f'Invalid tag: {tagname}')
			tag_offset = tag_map[tagname] - i
			if tag_offset < -2048 or tag_offset > 2047:
				raise Exception(f'Tag offset is too large: {tag_offset}')
			if tag_offset < 0:
				tag_offset = get_12_bit_twos_comp_negative(str(abs(tag_offset)))
			else:
				tag_offset = get_12_bit_memory_address(tag_offset)
			lower_right_imm, upper_left_imm, upper_right_imm = tag_offset[0:4], tag_offset[4:8], tag_offset[8:12]
			# verifying instructions
			if not isinstance(machine_instructions[i-5], SetMachineInstr) or machine_instructions[i-5].imm is not None:
				raise Exception(f'Invalid Branch Instruction State Detected, Expected Empty Set Instruction 5 indices earlier')
			if not isinstance(machine_instructions[i-4], MemMachineInstr) or machine_instructions[i-4].target_location != '200':
				raise Exception(f'Invalid Branch Instruction State Detected, Expected STR R7, 200 4 indices earlier')	
			if not isinstance(machine_instructions[i-3], SetMachineInstr) or machine_instructions[i-3].imm is not None:
				raise Exception(f'Invalid Branch Instruction State Detected, Expected Empty Set Instruction 3 indices earlier')
			if not isinstance(machine_instructions[i-2], SetMachineInstr) or machine_instructions[i-2].imm is not None:
				raise Exception(f'Invalid Branch Instruction State Detected, Expected Empty Set Instruction 2 indices earlier')
			if not isinstance(machine_instructions[i-1], MemMachineInstr) or machine_instructions[i-1].target_location != '201':
				raise Exception(f'Invalid Branch Instruction State Detected, Expected STR R7, 201 1 index before')
			first_set_instr = SetMachineInstr(mnemonic='SET', flag=True, imm=lower_right_imm)
			first_mem_instr = MemMachineInstr(mnemonic='MEM', is_load=False, target_reg=RESERVED_REGISTER_NAME, target_location='200')
			second_set_instr = SetMachineInstr(mnemonic='SET', flag=False, imm=upper_left_imm)
			third_set_instr = SetMachineInstr(mnemonic='SET', flag=True, imm=upper_right_imm)
			second_mem_instr = MemMachineInstr(mnemonic='MEM', is_load=False, target_reg=RESERVED_REGISTER_NAME, target_location='201')
			machine_instructions[i-5] = first_set_instr
			machine_instructions[i-4] = first_mem_instr
			machine_instructions[i-3] = second_set_instr
			machine_instructions[i-2] = third_set_instr
			machine_instructions[i-1] = second_mem_instr
	return machine_instructions

def encode_register_instruction(machine_instr: RegMachineInstr) -> str:
	valid_instructions = ['ADD', 'AND', 'XOR', 'ROL', 'MOV']
	if machine_instr.mnemonic not in valid_instructions:
		raise Exception(f'Invalid register instruction: {machine_instr}')
	opcode = get_opcode_bits(machine_instr.mnemonic)
	dest_reg = get_register_bits(machine_instr.dest_reg)
	src_reg = get_register_bits(machine_instr.src_reg)
	return opcode + dest_reg + src_reg

def encode_set_instruction(machine_instr: SetMachineInstr) -> str:
	if machine_instr.mnemonic != 'SET':
		raise Exception(f'Invalid SET instruction: {machine_instr}')
	opcode = get_opcode_bits(machine_instr.mnemonic)
	flag = '0' if machine_instr.flag == False else '1'
	imm = machine_instr.imm
	if len(imm) != 4:
		raise Exception(f'Invalid SET half immediate {imm} detected. Did you mean to zerofill the half immediate?')
	return opcode + '0' + flag + imm

def encode_mem_instruction(machine_instr: MemMachineInstr) -> str:
	if machine_instr.mnemonic != 'MEM':
		raise Exception(f'Invalid MEM instruction: {machine_instr}')
	opcode = get_opcode_bits(machine_instr.mnemonic)
	is_load = '0' if machine_instr.is_load == True else '1'
	target_reg = get_register_bits(machine_instr.target_reg)
	if machine_instr.target_location == RESERVED_REGISTER_NAME:
		return opcode + target_reg + is_load + '00'
	elif machine_instr.target_location == '200':
		return opcode + target_reg + is_load + '01'
	elif machine_instr.target_location == '201':
		return opcode + target_reg + is_load + '10'	
	else:
		raise Exception(f'Invalid branch target location detected: {machine_instr.target_location}')

def encode_brn_instruction(machine_instr: BrnMachineInstr) -> str:
	if machine_instr.mnemonic != 'BEQ':
		raise Exception(f'Invalid BEQ instruction: {machine_instr}')
	opcode = get_opcode_bits(machine_instr.mnemonic)
	operand_reg1 = get_register_bits(machine_instr.operand_reg1)
	operand_reg2 = get_register_bits(machine_instr.operand_reg2)
	return opcode + operand_reg1 + operand_reg2

def encode_machine_instruction(machine_instr: MachineInstruction) -> str:
	if isinstance(machine_instr, RegMachineInstr):
		return encode_register_instruction(machine_instr)
	elif isinstance(machine_instr, SetMachineInstr):
		return encode_set_instruction(machine_instr)
	elif isinstance(machine_instr, MemMachineInstr):
		return encode_mem_instruction(machine_instr)
	elif isinstance(machine_instr, BrnMachineInstr):
		return encode_brn_instruction(machine_instr)
	else:
		raise Exception(f'Invalid machine instruction: {machine_instr}')

def encode_machine_instructions(machine_instructions: [MachineInstruction]) -> [str]:
	encoded_machine_instructions = []
	for machine_instr in machine_instructions:
		encoded_machine_instructions.append(encode_machine_instruction(machine_instr))
	return encoded_machine_instructions

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-i', '--input', help='Input File Path', required=True)
	parser.add_argument('-o', '--output', help='Output File Path', required=True)
	args = parser.parse_args()
	return args

def main():
	# use argparse to parse the arguments
	# python3 assembler.py -i <input_file> -o <output_file>
	args = parse_args()
	source_file = args.input
	output_file = args.output
	cleaned_lines = get_cleaned_lines(source_file)
	source_artifacts = get_source_artifacts(cleaned_lines)
	intermediate_instructions = process_source_artifacts(source_artifacts)
	machine_instructions = process_intermediate_instructions(intermediate_instructions)
	machine_instructions = extract_tag_information(machine_instructions)
	machine_instructions = tag_branch_instructions(machine_instructions)
	encoded_machine_instructions = encode_machine_instructions(machine_instructions)
	for (machine_instruction, encoded_machine_instruction) in zip(machine_instructions, encoded_machine_instructions):
		print(f'{encoded_machine_instruction} <- {machine_instruction}')
	write_machine_code(output_file, encoded_machine_instructions)

if __name__ == '__main__':
	main()