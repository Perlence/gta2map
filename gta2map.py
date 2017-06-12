from contextlib import contextmanager
from ctypes import windll, byref, create_string_buffer, c_ulong
from struct import unpack

import attr
import pyglet


@attr.s
class App:
    process_handle = attr.ib()

    window = attr.ib(default=None)
    map_sprite = attr.ib(default=None)
    pin_sprite = attr.ib(default=None)

    def __attrs_post_init__(self):
        if self.window is None:
            self.window = pyglet.window.Window(768, 768)

        if self.map_sprite is None:
            map_image = pyglet.image.load('./gfx/Residential_satellite_map.png')
            self.map_sprite = pyglet.sprite.Sprite(map_image)

        if self.pin_sprite is None:
            pin_image = pyglet.image.load('./gfx/pin.png')
            pin_image.anchor_x = pin_image.width // 2
            pin_image.anchor_y = 0
            self.pin_sprite = pyglet.sprite.Sprite(pin_image)
            self.pin_sprite.scale = 0.1

        self.window.event(self.on_draw)
        pyglet.clock.schedule(self.on_update)

    def on_draw(self):
        self.window.clear()
        self.map_sprite.draw()
        self.pin_sprite.draw()

    def on_update(self, dt):
        real_x, real_y = get_coordinates(self.process_handle)
        self.pin_sprite.x = real_x * 768 / 2 ** 22
        self.pin_sprite.y = 768 - real_y * 768 / 2 ** 22


@contextmanager
def open_process(pid):
    OpenProcess = windll.kernel32.OpenProcess
    CloseHandle = windll.kernel32.CloseHandle
    PROCESS_ALL_ACCESS = 0x1F0FFF
    process_handle = OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    yield process_handle
    CloseHandle(process_handle)


def get_coordinates(process_handle):
    X_POS_ADDR = 0x5de030
    Y_POS_ADDR = 0x5de034
    x_pos, = unpack('<I', read_process_bytes(process_handle, X_POS_ADDR, 4))
    y_pos, = unpack('<I', read_process_bytes(process_handle, Y_POS_ADDR, 4))
    return x_pos, y_pos


def read_process_bytes(process_handle, address, size):
    buffer = create_string_buffer(size)
    buffer_size = size
    bs, _ = read_process_memory(process_handle, address, buffer, buffer_size)
    return bs


def read_process_memory(process_handle, address, buffer, buffer_size):
    bytes_read = c_ulong(0)
    ReadProcessMemory = windll.kernel32.ReadProcessMemory
    ok = ReadProcessMemory(process_handle, address, buffer, buffer_size, byref(bytes_read))
    if not ok:
        raise RuntimeError('ReadProcessMemory is not ok')
    return buffer, bytes_read.value


def main():
    pid = int(input())
    with open_process(pid) as ph:
        app = App(ph)  # noqa
        pyglet.app.run()


if __name__ == '__main__':
    main()
