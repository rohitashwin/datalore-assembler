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

def get_half_imms(imm: str) -> (str, str):
	imm = int(imm)
	imm = bin(imm)[2:]
	if len(imm) < 8:
		imm = '0' * (8 - len(imm)) + imm
	elif len(imm) > 8:
		raise Exception(f'Immediate value {imm} is too large')
	return imm[:4], imm[4:]

def get_12_bit_memory_address(num: str) -> str:
	num = int(num)
	if num < 0:
		raise Exception('Only positive numbers can be converted to 12 bit representations. Did you mean you apply abs()?')
	num = bin(num)[2:]
	num = num.zfill(12)
	if len(num) > 12:
		raise Exception(f'Address offset value {num} is too large')
	return num

def get_12_bit_twos_comp_negative(num: str) -> str:
	num = get_12_bit_memory_address(num)
	num = num.replace('0', 'x')
	num = num.replace('1', '0')
	num = num.replace('x', '1')
	num = bin(int(num, 2) + 1)[2:]
	if len(num) > 12:
		raise Exception(f'Address offset value {num} is too small')
	return num

def get_twos_complement_negative(num: str) -> str:
	num = int(num)
	num = bin(num)[2:]
	if len(num) < 8:
		num = '0' * (8 - len(num)) + num
	elif len(num) > 8:
		raise Exception(f'Immediate value {num} is too large')
	num = num.replace('0', 'x')
	num = num.replace('1', '0')
	num = num.replace('x', '1')
	num = bin(int(num, 2) + 1)[2:]
	if len(num) < 8:
		num = '0' * (8 - len(num)) + num
	elif len(num) > 8:
		raise Exception(f'Immediate value {num} is too large')
	return num

def write_machine_code(output_file :str, machine_code: [str]):
	with open(output_file, 'w') as f:
		for line in machine_code:
			f.write(line + '\n')

def get_mask_bits_rtl(num: int) -> str:
	# eg: (2) -> 0b11111100
	# eg: (3) -> 0b11111000
	mask = 0
	for i in range(num):
		mask += 2 ** (7 - i)
	return bin(mask)[2:]

if __name__ == '__main__':
	print(get_twos_complement_negative('56'))
	# expected: 200