import struct

class TBFHeader:
	'''
	Tock Binary Format header class. This can parse TBF encoded headers and
	return various properties of the application.
	'''

	HEADER_TYPE_MAIN                    = 0x01
	HEADER_TYPE_WRITEABLE_FLASH_REGIONS = 0x02
	HEADER_TYPE_PACKAGE_NAME            = 0x03
	HEADER_TYPE_PIC_OPTION_1            = 0x04
	HEADER_TYPE_PERMISSIONS             = 0x06

	def __init__ (self, buffer):
		self.valid = False
		self.is_app = False
		self.fields = {}

		full_buffer = buffer;

		# Need at least a version number
		if len(buffer) < 2:
			return

		# Get the version number
		self.version = struct.unpack('<H', buffer[0:2])[0]
		buffer = buffer[2:]

		if self.version == 1 and len(buffer) >= 74:
			checksum = self._checksum(full_buffer[0:72])
			buffer = buffer[2:]
			base = struct.unpack('<IIIIIIIIIIIIIIIIII', buffer[0:72])
			buffer = buffer[72:]
			self.fields['total_size'] = base[0]
			self.fields['entry_offset'] = base[1]
			self.fields['rel_data_offset'] = base[2]
			self.fields['rel_data_size'] = base[3]
			self.fields['text_offset'] = base[4]
			self.fields['text_size'] = base[5]
			self.fields['got_offset'] = base[6]
			self.fields['got_size'] = base[7]
			self.fields['data_offset'] = base[8]
			self.fields['data_size'] = base[9]
			self.fields['bss_mem_offset'] = base[10]
			self.fields['bss_mem_size'] = base[11]
			self.fields['min_stack_len'] = base[12]
			self.fields['min_app_heap_len'] = base[13]
			self.fields['min_kernel_heap_len'] = base[14]
			self.fields['package_name_offset'] = base[15]
			self.fields['package_name_size'] = base[16]
			self.fields['checksum'] = base[17]
			self.is_app = True

			if checksum == self.fields['checksum']:
				self.valid = True

		elif self.version == 2 and len(buffer) >= 14:
			base = struct.unpack('<HIII', buffer[:14])
			print('hey, I got the buffer to be %s' % hex(int.from_bytes(buffer[:14], 'big')))
			buffer = buffer[14:]
			self.fields['header_size'] = base[0]
			self.fields['total_size'] = base[1]
			self.fields['flags'] = base[2]
			self.fields['checksum'] = base[3]
			print('hey, I got the checksum to equal %s!'% hex(self.fields['checksum']))

			# permission bit mappings
			# NOTE: it's crucial that this mapping stays in sync with the one in Tock
			# lest a user grant access to the wrong hardware.
			self.permission_bits = {
				'ADC': 5,
				'ALARM': 0,
				'AMBIENT_LIGHT': 20,
				'ANALOG_COMPARATOR': 7,
				'APP_FLASH': 15,
				'BLE_ADVERTISING': 11,
				'BUTTON': 3,
				'CONSOLE': 1,
				'CRC': 13,
				'DAC': 6,
				'GPIO': 4,
				'GPIO_ASYNC': 28,
				'HUMIDITY': 19,
				'I2C_MASTER': 14,
				'I2C_MASTER_SLAVE': 10,
				'LED': 2,
				'LPS25HB': 24,
				'LTC294X': 25,
				'MAX17205': 26,
				'NINEDOF': 21,
				'NRF51822_SERIALIZATION': 29,
				'NVM_STORAGE': 16,
				'PCA9544A': 27,
				'RNG': 12,
				'SD_CARD': 17,
				'SPI': 8,
				'TEMPERATURE': 18,
				'TMP006': 23,
				'TSL2561': 22,
				'USB_USER': 9
			}

			if len(full_buffer) >= self.fields['header_size']:
				# Zero out checksum for checksum calculation.
				print(self.fields['header_size'])
				nbuf = bytearray(self.fields['header_size'])
				nbuf[:] = full_buffer[0:self.fields['header_size']]
				struct.pack_into('<I', nbuf, 12, 0)
				checksum = self._checksum(nbuf)

				remaining = self.fields['header_size'] - 16

				# Now check to see if this is an app or padding.
				if remaining > 0 and len(buffer) >= remaining:
					# This is an application. That means we need more parsing.
					self.is_app = True
					self.writeable_flash_regions = []

					def roundup (x, to):
						return x if x % to == 0 else x + to - x % to

					while remaining >= 4:
						base = struct.unpack('<HH', buffer[0:4])
						buffer = buffer[4:]
						tipe = base[0]
						length = base[1]

						remaining -= 4

						if tipe == self.HEADER_TYPE_MAIN:
							if remaining >= 12 and length == 12:
								base = struct.unpack('<III', buffer[0:12])
								self.fields['init_fn_offset'] = base[0]
								self.fields['protected_size'] = base[1]
								self.fields['minimum_ram_size'] = base[2]

						elif tipe == self.HEADER_TYPE_WRITEABLE_FLASH_REGIONS:
							if remaining >= length:
								for i in range(0, int(length / 8)):
									base = struct.unpack('<II', buffer[i*8:(i+1)*8])
									# Add offset,length.
									self.writeable_flash_regions.append((base[0], base[1]))

						elif tipe == self.HEADER_TYPE_PACKAGE_NAME:
							if remaining >= length:
								self.package_name = buffer[0:length].decode('utf-8')

						elif tipe == self.HEADER_TYPE_PIC_OPTION_1:
							if remaining >= 40 and length == 40:
								base = struct.unpack('<IIIIIIIIII', buffer[0:40])
								self.fields['text_offset'] = base[0]
								self.fields['data_offset'] = base[1]
								self.fields['data_size'] = base[2]
								self.fields['bss_memory_offset'] = base[3]
								self.fields['bss_size'] = base[4]
								self.fields['relocation_data_offset'] = base[5]
								self.fields['relocation_data_size'] = base[6]
								self.fields['got_offset'] = base[7]
								self.fields['got_size'] = base[8]
								self.fields['minimum_stack_length'] = base[9]

								self.pic_strategy = 'C Style'

						elif tipe == self.HEADER_TYPE_PERMISSIONS:
							if remaining >= 8 and length == 8:
								base = struct.unpack('<Q', buffer[0:8])
								self.fields['permissions'] = base[0]
								print('hey, I got the permissions to equal %s!'% hex(self.fields['permissions']))
							else:
								print('wahhhhhhhhhhhhhh')

						else:
							print('Warning: Unknown TLV block in TBF header: %d.' % tipe)
							print('Warning: You might want to update tockloader.')

						# All blocks are padded to four byte, so we may need to
						# round up.
						length = roundup(length, 4)
						buffer = buffer[length:]
						remaining -= length

					if checksum == self.fields['checksum']:
						self.valid = True
					else:
						print('Checksum mismatch. in packet: {:#x}, calculated: {:#x}'.format(self.fields['checksum'], checksum))

				else:
					# This is just padding and not an app.
					if checksum == self.fields['checksum']:
						self.valid = True

	def is_valid (self):
		'''
		Whether the CRC and other checks passed for this header.
		'''
		return self.valid

	def is_enabled (self):
		'''
		Whether the application is marked as enabled. Enabled apps start when
		the board boots, and disabled ones do not.
		'''
		if not self.valid:
			return False
		elif self.version == 1:
			# Version 1 apps don't have this bit so they are just always enabled
			return True
		else:
			return self.fields['flags'] & 0x01 == 0x01

	def is_sticky (self):
		'''
		Whether the app is marked sticky and won't be erase during normal app
		erases.
		'''
		if not self.valid:
			return False
		elif self.version == 1:
			# No sticky bit in version 1, so they are not sticky
			return False
		else:
			return self.fields['flags'] & 0x02 == 0x02

	def set_flag (self, flag_name, flag_value):
		'''
		Set a flag in the TBF header.

		Valid flag names: `enable`, `sticky`
		'''
		if self.version == 1 or not self.valid:
			return

		if flag_name == 'enable':
			if flag_value:
				self.fields['flags'] |= 0x01;
			else:
				self.fields['flags'] &= ~0x01;

		elif flag_name == 'sticky':
			if flag_value:
				self.fields['flags'] |= 0x02;
			else:
				self.fields['flags'] &= ~0x02;

	def set_permission (self, name, value):
		'''
		Set a permission in the TBF header.
		Permissions are represented by a u64, with each driver
		corresponding to a specific bit.
		'''
		if self.version == 1 or not self.valid:
			return

		bit = self.permission_bits.get(name.upper())
		if bit == None:
			print('error: permission bit does not exist')
			return

		if value.lower() == 'true' or value.lower() == 't' or value == '1':
			self.fields['permissions'] |= 1 << bit
			print('Successfully allowed %s'%name)
		else:
			self.fields['permissions'] &= ~(1 << bit)
			print('Successfully disallowed %s'%name)

	def list_permissions (self):
		'''
		Set a permission in the TBF header.
		Permissions are represented by a u64, with each driver
		corresponding to a specific bit.
		'''
		if self.version == 1 or not self.valid:
			return

		print('%s: %s' % (self.get_app_name(), '{:b}'.format(self.fields['permissions'])))

	def get_app_size (self):
		'''
		Get the total size the app takes in bytes in the flash of the chip.
		'''
		return self.fields['total_size']

	def get_header_size (self):
		'''
		Get the size of the header in bytes. This includes any alignment
		padding at the end of the header.
		'''
		if self.version == 1:
			return 74
		else:
			return self.fields['header_size']

	def get_app_name (self):
		'''
		Return the package name if it was encoded in the header, otherwise
		return a tuple of (package_name_offset, package_name_size).
		'''
		if hasattr(self, 'package_name'):
			return self.package_name
		elif 'package_name_offset' in self.fields and 'package_name_size' in self.fields:
			return (self.fields['package_name_offset'], self.fields['package_name_size'])
		else:
			return ''

	# Return a buffer containing the header repacked as a binary buffer
	def get_binary (self):
		'''
		Get the TBF header in a bytes array.
		'''
		if self.version == 1:
			buf = struct.pack('<IIIIIIIIIIIIIIIIIII',
				self.version, self.fields['total_size'], self.fields['entry_offset'],
				self.fields['rel_data_offset'], self.fields['rel_data_size'],
				self.fields['text_offset'], self.fields['text_size'],
				self.fields['got_offset'], self.fields['got_size'],
				self.fields['data_offset'], self.fields['data_size'],
				self.fields['bss_mem_offset'], self.fields['bss_mem_size'],
				self.fields['min_stack_len'], self.fields['min_app_heap_len'],
				self.fields['min_kernel_heap_len'], self.fields['package_name_offset'],
				self.fields['package_name_size'])
			checksum = self._checksum(buf)
			buf += struct.pack('<I', checksum)

		elif self.version == 2:
			buf = struct.pack('<HHIII',
				self.version, self.fields['header_size'], self.fields['total_size'],
				self.fields['flags'], 0)
			if self.is_app:
				buf += struct.pack('<HHIII',
					self.HEADER_TYPE_MAIN, 12,
					self.fields['init_fn_offset'], self.fields['protected_size'],
					self.fields['minimum_ram_size'])
				if hasattr(self, 'writeable_flash_regions'):
					buf += struct.pack('<HH',
						self.HEADER_TYPE_WRITEABLE_FLASH_REGIONS,
						len(self.writeable_flash_regions) * 8)
					for wfr in self.writeable_flash_regions:
						buf += struct.pack('<II', wfr[0], wfr[1])
				if hasattr(self, 'pic_strategy'):
					if self.pic_strategy == 'C Style':
						buf += struct.pack('<HHIIIIIIIIII',
							self.HEADER_TYPE_PIC_OPTION_1, 40,
							self.fields['text_offset'], self.fields['data_offset'],
							self.fields['data_size'], self.fields['bss_memory_offset'],
							self.fields['bss_size'], self.fields['relocation_data_offset'],
							self.fields['relocation_data_size'], self.fields['got_offset'],
							self.fields['got_size'], self.fields['minimum_stack_length'])
				if hasattr(self, 'package_name'):
					encoded_name = self.package_name.encode('utf-8')
					buf += struct.pack('<HH', self.HEADER_TYPE_PACKAGE_NAME, len(encoded_name))
					buf += encoded_name

			nbuf = bytearray(len(buf))
			nbuf[:] = buf
			buf = nbuf

			checksum = self._checksum(buf)
			struct.pack_into('<I', buf, 12, checksum)

		return buf

	def _checksum (self, buffer):
		'''
		Calculate the TBF header checksum.
		'''
		# Add 0s to the end to make sure that we are multiple of 4.
		padding = len(buffer) % 4
		if padding != 0:
			padding = 4 - padding
			buffer += bytes([0]*padding)

		# Loop throw
		checksum = 0
		for i in range(0, len(buffer), 4):
			checksum ^= struct.unpack('<I', buffer[i:i+4])[0]

		return checksum

	def __str__ (self):
		out = ''
		if not self.valid:
			out += 'INVALID!\n'
		if hasattr(self, 'package_name'):
			out += '{:<22}: {}\n'.format('package_name', self.package_name)
		if hasattr(self, 'pic_strategy'):
			out += '{:<22}: {}\n'.format('PIC', self.pic_strategy)
		out += '{:<22}: {:>8}\n'.format('version', self.version)
		if hasattr(self, 'writeable_flash_regions'):
			for i, wfr in enumerate(self.writeable_flash_regions):
				out += 'writeable flash region {}\n'.format(i)
				out += '  {:<20}: {:>8} {:>#12x}\n'.format('offset', wfr[0], wfr[0])
				out += '  {:<20}: {:>8} {:>#12x}\n'.format('length', wfr[1], wfr[1])
		for k,v in sorted(self.fields.items()):
			if k == 'checksum':
				out += '{:<22}:          {:>#12x}\n'.format(k, v)
			else:
				out += '{:<22}: {:>8} {:>#12x}\n'.format(k, v, v)

			if k == 'flags':
				values = ['No', 'Yes']
				out += '  {:<20}: {}\n'.format('enabled', values[(v >> 0) & 0x01])
				out += '  {:<20}: {}\n'.format('sticky', values[(v >> 1) & 0x01])
		return out
