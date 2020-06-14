import moderngl_window as mglw
from moderngl_window.scene.camera import KeyboardCamera, OrbitCamera


class OrbitCameraWindow(mglw.WindowConfig):
    """Base class with built in 3D orbit camera support"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera = OrbitCamera(
            aspect_ratio=self.wnd.aspect_ratio, far=5000.0, target=(256, 0, 256), radius=100, angles=(0.465, -1.35)
        )

        self.camera.zoom_sensitivity = 5.0
        self.wnd.mouse_exclusivity = True
        self.camera_enabled = True

    def key_event(self, key, action, modifiers):
        keys = self.wnd.keys

        if action == keys.ACTION_PRESS:
            if key == keys.C:
                self.camera_enabled = not self.camera_enabled
                self.wnd.mouse_exclusivity = self.camera_enabled
                self.wnd.cursor = not self.camera_enabled
            if key == keys.SPACE:
                self.timer.toggle_pause()

    def mouse_position_event(self, x: int, y: int, dx, dy):
        if self.camera_enabled:
            self.camera.rot_state(dx, dy)

    def mouse_scroll_event(self, x_offset: float, y_offset: float):
        if self.camera_enabled:
            self.camera.zoom_state(y_offset)

    def resize(self, width: int, height: int):
        self.camera.projection.update(aspect_ratio=self.wnd.aspect_ratio)


class CameraWindow(mglw.WindowConfig):
    """Base class with built in 3D camera support"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.camera = KeyboardCamera(self.wnd.keys, aspect_ratio=self.wnd.aspect_ratio, far=5000)
        self.camera.set_rotation(45, 0)
        self.camera.set_position(-5, 25, -5)
        self.camera.mouse_sensitivity = 0.25

        self.camera_enabled = True

    def key_event(self, key, action, modifiers):
        keys = self.wnd.keys

        if self.camera_enabled:
            if modifiers.shift:
                self.camera.velocity = 100.0
            else:
                self.camera.velocity = 5.0
            self.camera.key_input(key, action, modifiers)

        if action == keys.ACTION_PRESS:
            if key == keys.C:
                self.camera_enabled = not self.camera_enabled
                self.wnd.mouse_exclusivity = self.camera_enabled
                self.wnd.cursor = not self.camera_enabled
            if key == keys.SPACE:
                self.timer.toggle_pause()

    def mouse_position_event(self, x: int, y: int, dx, dy):
        if self.camera_enabled:
            self.camera.rot_state(-dx, -dy)

    def resize(self, width: int, height: int):
        self.camera.projection.update(aspect_ratio=self.wnd.aspect_ratio)

    def render(self, time: float, frame_time: float):
        pass
