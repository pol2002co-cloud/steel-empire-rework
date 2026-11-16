"""Compile freestanding x86 event code for a fixed address inside .rework."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools/python-deps-v093'))
import pefile

ZIG = ROOT/'tools/zig/zig-x86_64-windows-0.17.1/zig.exe'
REWORK_START = 0x53b000
REWORK_END = REWORK_START+0x80000
IMAGE_BASE_ALIGNMENT = 0x10000


def _export_name(name):
    return re.sub(r'@\d+$', '', name[1:] if name.startswith('_') else name)


def _fix_at_linked_base(path, image_base):
    """Discard only verified rebase hints; linked code addresses stay untouched."""
    pe = pefile.PE(data=Path(path).read_bytes(), fast_load=False)
    try:
        if pe.FILE_HEADER.Machine != 0x14c or pe.OPTIONAL_HEADER.ImageBase != image_base:
            raise ValueError('Cannot fix an image linked for another architecture/base')
        size = pe.OPTIONAL_HEADER.SizeOfImage
        directory = pe.OPTIONAL_HEADER.DATA_DIRECTORY[5]
        if bool(directory.VirtualAddress) != bool(directory.Size):
            raise ValueError('Malformed rebase-hint directory')
        seen = set()
        consumed = 0
        for block in getattr(pe,'DIRECTORY_ENTRY_BASERELOC',()):
            block_size = block.struct.SizeOfBlock
            if block_size < 8 or block_size % 2 or consumed+block_size > directory.Size:
                raise ValueError('Malformed rebase-hint block')
            if len(block.entries)*2 != block_size-8:
                raise ValueError('Incomplete rebase-hint block')
            consumed += block_size
            for relocation in block.entries:
                if relocation.type == 0:
                    continue
                if relocation.type != 3 or relocation.rva in seen:
                    raise ValueError('Only unique x86 HIGHLOW rebase hints are allowed')
                seen.add(relocation.rva)
                if not any(section.VirtualAddress <= relocation.rva and
                           relocation.rva+4 <= section.VirtualAddress+section.Misc_VirtualSize
                           for section in pe.sections):
                    raise ValueError('Rebase hint points outside a mapped section')
                pointer = pe.get_dword_at_rva(relocation.rva)
                if pointer is None or not image_base <= pointer < image_base+size:
                    raise ValueError('Rebase hint contains a non-image pointer')
        if consumed != directory.Size:
            raise ValueError('Incomplete rebase-hint directory')
        directory.VirtualAddress = 0
        directory.Size = 0
        pe.FILE_HEADER.Characteristics |= 1  # IMAGE_FILE_RELOCS_STRIPPED
        pe.OPTIONAL_HEADER.DllCharacteristics &= ~0x60  # No ASLR/high-entropy VA.
        pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()
        pe.write(filename=str(path))
    finally:
        pe.close()


def read_image(path, image_base, exports):
    """Validate the linked image before any of its bytes enter the game."""
    if image_base % IMAGE_BASE_ALIGNMENT or not REWORK_START <= image_base < REWORK_END:
        raise ValueError('C image base must be 64K-aligned inside .rework')
    names = list(exports)
    if not names or len(names) != len(set(names)) or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) for name in names):
        raise ValueError('Expected unique C export names')
    pe = pefile.PE(str(path), fast_load=False)
    try:
        if pe.FILE_HEADER.Machine != 0x14c or pe.OPTIONAL_HEADER.Magic != 0x10b:
            raise ValueError('Event image must be PE32 x86')
        if pe.OPTIONAL_HEADER.ImageBase != image_base:
            raise ValueError('Event image was linked at the wrong fixed address')
        if pe.OPTIONAL_HEADER.AddressOfEntryPoint:
            raise ValueError('Freestanding event image must not have a DLL entry point')
        size = pe.OPTIONAL_HEADER.SizeOfImage
        if size <= 0 or image_base+size > REWORK_END:
            raise ValueError('Event image exceeds .rework capacity')
        for index, label in ((1,'imports'), (5,'relocations'), (9,'TLS'), (12,'IAT'), (13,'delay imports')):
            directory = pe.OPTIONAL_HEADER.DATA_DIRECTORY[index]
            if directory.VirtualAddress or directory.Size:
                raise ValueError('Freestanding event image contains '+label)
        for section in pe.sections:
            if section.Misc_VirtualSize or section.SizeOfRawData:
                if section.Characteristics & 0x80000000:
                    raise ValueError('Writable event section: '+section.Name.rstrip(b'\0').decode('ascii', 'replace'))
                if not section.Characteristics & 0x40000000:
                    raise ValueError('Event sections must be readable')
                if section.VirtualAddress+max(section.Misc_VirtualSize,section.SizeOfRawData) > size:
                    raise ValueError('Event section exceeds declared mapped image')
        available = {}
        symbols = pe.DIRECTORY_ENTRY_EXPORT.symbols if hasattr(pe,'DIRECTORY_ENTRY_EXPORT') else ()
        for symbol in symbols:
            if symbol.forwarder:
                raise ValueError('Forwarded event export is not freestanding')
            if symbol.name is None:
                continue
            raw_name = symbol.name.decode('ascii')
            normalized = raw_name if raw_name in names else _export_name(raw_name)
            if normalized not in names:
                continue
            if normalized in available:
                raise ValueError('Ambiguous event export: '+normalized)
            if not any(section.Characteristics & 0x20000000 and
                       section.VirtualAddress <= symbol.address < section.VirtualAddress+section.Misc_VirtualSize
                       for section in pe.sections):
                raise ValueError('Event export does not point into executable code: '+normalized)
            available[normalized] = image_base+symbol.address
        missing = set(names)-available.keys()
        if missing:
            raise ValueError('Missing event exports: '+', '.join(sorted(missing)))
        mapped = pe.get_memory_mapped_image()
        if len(mapped) > size:
            raise ValueError('Mapped event image exceeds SizeOfImage')
        return mapped.ljust(size,b'\0'), available
    finally:
        pe.close()


def compile_image(sourcePath, generatedIncludeDir, imageBase, outputPath, exports):
    source = Path(sourcePath).resolve(strict=True)
    include = Path(generatedIncludeDir).resolve(strict=True)
    output = Path(outputPath).resolve()
    if not include.is_dir() or not source.is_file() or output == source or output.suffix.lower() != '.dll':
        raise ValueError('Expected C source, include directory and a separate output DLL')
    if imageBase % IMAGE_BASE_ALIGNMENT or not REWORK_START <= imageBase < REWORK_END:
        raise ValueError('C image base must be 64K-aligned inside .rework')
    if not ZIG.is_file():
        raise FileNotFoundError('Verified project-local Zig is required: '+str(ZIG))
    output.parent.mkdir(parents=True,exist_ok=True)
    command = [str(ZIG),'cc','-target','x86-windows-msvc','-shared','-nostdlib',
               '-ffreestanding','-fno-builtin','-fno-stack-protector','-mno-stack-arg-probe',
               '-Oz','-Wl,--no-entry',f'-Wl,--image-base,{imageBase:#x}',
               '-I',str(include),str(source),'-o',str(output)]
    result = subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    if result.returncode:
        raise RuntimeError('Event C compilation failed:\n'+result.stdout+result.stderr)
    # Zig's cc driver accepts GNU spelling, but not MSVC /fixed or /noentry.
    _fix_at_linked_base(output,imageBase)
    return read_image(output,imageBase,exports)
