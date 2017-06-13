from contextlib import contextmanager
from ctypes import windll, byref, create_string_buffer, c_ulong
from os.path import basename
from struct import unpack, calcsize

import attr
import pyglet
import win32api
import win32process


def main():
    import sys

    if len(sys.argv) < 2:
        sys.exit('usage: gta2map PID')

    pid = int(sys.argv[1])
    with open_process(pid) as ph:
        app = App(ph)  # noqa
        pyglet.app.run()


@attr.s
class App:
    process_handle = attr.ib()

    window = attr.ib(init=False, repr=False)
    map_sprite = attr.ib(init=False, repr=False)
    player_sprite = attr.ib(init=False, repr=False)
    target_sprite = attr.ib(init=False, repr=False)

    def __attrs_post_init__(self):
        self.window = pyglet.window.Window(768, 768)

        map_image = pyglet.image.load('./gfx/res-6p.jpg')
        self.map_sprite = pyglet.sprite.Sprite(map_image)
        self.map_sprite.scale = 768 / map_image.width

        pin_image = pyglet.image.load('./gfx/pin.png')
        pin_image.anchor_x = pin_image.width // 2
        pin_image.anchor_y = 0
        self.player_sprite = pyglet.sprite.Sprite(pin_image)
        self.player_sprite.scale = 0.1
        self.target_sprite = pyglet.sprite.Sprite(pin_image)
        self.target_sprite.scale = 0.1

        self.window.event(self.on_draw)
        pyglet.clock.schedule(self.on_update)

    def on_draw(self):
        self.map_sprite.draw()
        self.player_sprite.draw()
        self.target_sprite.draw()

    def on_update(self, dt):
        max_coordinate = 1 << 22
        real_x, real_y = get_coordinates(self.process_handle)
        self.player_sprite.x = real_x * self.map_sprite.width / max_coordinate
        self.player_sprite.y = self.map_sprite.height - real_y * self.map_sprite.height / max_coordinate

        real_x, real_y = get_target_coordinates(self.process_handle)
        if real_x is None or real_y is None:
            self.target_sprite.visible = False
        else:
            self.target_sprite.visible = True
            self.target_sprite.x = real_x * self.map_sprite.width / 2 ** 22
            self.target_sprite.y = self.map_sprite.height - real_y * self.map_sprite.height / 2 ** 22


@contextmanager
def open_process(pid):
    PROCESS_ALL_ACCESS = 0x1F0FFF
    handle = win32api.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    yield handle
    handle.close()


def get_coordinates(process_handle):
    x_pos_addr = 0x5de030
    y_pos_addr = 0x5de034
    (x_pos,) = unpack('<I', read_process_bytes(process_handle, x_pos_addr))
    (y_pos,) = unpack('<I', read_process_bytes(process_handle, y_pos_addr))
    return x_pos, y_pos


def get_target_coordinates(process_handle):
    base_address = ('gta2.exe', 0x282f40)
    is_target_visible_offsets = (0x12cc, 0x1290, 0x10)
    x_pos_offsets = (0x12cc, 0x1290, 0x14)
    y_pos_offsets = (0x12cc, 0x1290, 0x18)
    (is_target_visible,) = unpack('<I', read_process_bytes(process_handle, base_address, *is_target_visible_offsets))
    if not is_target_visible:
        return None, None
    (x_pos,) = unpack('<I', read_process_bytes(process_handle, base_address, *x_pos_offsets))
    (y_pos,) = unpack('<I', read_process_bytes(process_handle, base_address, *y_pos_offsets))
    return x_pos, y_pos


def read_process_bytes(process_handle, address, *offsets, fmt='I'):
    if isinstance(address, tuple):
        address = get_module_offset(process_handle, *address)

    size = calcsize(fmt)
    buffer = create_string_buffer(size)

    bs, _ = read_process_memory(process_handle, address, buffer, size)
    for offset in offsets:
        (address,) = unpack('<' + fmt, bs)
        address += offset
        bs, _ = read_process_memory(process_handle, address, buffer, size)

    return bs


def get_module_offset(process_handle, module_name, offset):
    handle = get_module_handle(process_handle, module_name)
    return handle + offset


def get_module_handle(process_handle, module_name):
    for hmod in win32process.EnumProcessModules(process_handle):
        module_full_name = win32process.GetModuleFileNameEx(process_handle, hmod)
        if basename(module_full_name) == module_name:
            return hmod


def read_process_memory(process_handle, address, buffer, buffer_size):
    bytes_read = c_ulong(0)
    ReadProcessMemory = windll.kernel32.ReadProcessMemory
    ok = ReadProcessMemory(process_handle.handle, address, buffer, buffer_size, byref(bytes_read))
    if not ok:
        raise RuntimeError('ReadProcessMemory is not ok')
    return buffer, bytes_read.value


if __name__ == '__main__':
    main()
