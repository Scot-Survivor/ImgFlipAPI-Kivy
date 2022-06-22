import os
import requests
import typing
import pickle
import tqdm
import enum
from api import caption_meme, get_memes

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.logger import Logger

from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import AsyncImage


class WindowsKeyboard(enum.Enum):
    RIGHT_ARROW = 79
    LEFT_ARROW = 80
    SPACE_BAR = 44
    BACKSPACE = 42


class InfoWindow(GridLayout):
    Next = ""

    def __init__(self, **kwargs):
        super(InfoWindow, self).__init__(**kwargs)
        if self.Next == "" and RunApp.ScreenManager.current == "Info":
            raise Exception("Invalid Info Page.")

        # Add just one column
        self.cols = 1
        self.rows = 2

        # Add one label for a message
        self.MessageLabel = Label(font_size=30)
        self.Continue = Button(text="Continue", color=(1, 1, 1, 1), size_hint=(1, .1))
        self.Continue.bind(on_release=self.continue_bind)

        # By default, every widget returns it's side as [100, 100], it gets finally resized,
        # but we have to listen for size change to get a new one
        # more: https://github.com/kivy/kivy/issues/1044
        self.MessageLabel.bind(width=self.update_text_width)

        # Add Label to layout
        self.add_widget(self.MessageLabel)
        self.add_widget(self.Continue)

    def continue_bind(self, *_):
        RunApp.ScreenManager.current = self.Next
        self.Next = ""

    def update_info(self, message):
        self.MessageLabel.text = message

    def update_text_width(self, *_):
        self.MessageLabel.text_size = (self.MessageLabel.width * 0.9, None)


class TemplateMeme:
    def __init__(self, meme_id, meme_name, meme_url, width, height, box_count):
        self.id = meme_id
        self.name = meme_name
        self.url = meme_url
        self.width = width
        self.height = height
        self.box_count = box_count
        self._file_path = ""

    def get_file_path(self):
        if self._file_path == "":
            try:
                os.mkdir('./cache/templates')
            except FileExistsError:
                pass
            self._file_path = f"./cache/templates/{self.id}.jpg"

            response = requests.get(self.url)
            with open(self._file_path, 'wb') as f:
                f.write(response.content)
                f.close()
        return self._file_path

    def get_box_count(self):
        return self.box_count

    def __reduce__(self):
        return TemplateMeme, (self.id, self.name, self.url, self.width, self.height, self.box_count)


class MemeClass:
    def __init__(self, meme_id, top_text, bottom_text, box_count, image_url):
        self.id = meme_id
        self.top_text = top_text
        self.bottom_text = bottom_text
        self.box_count = box_count
        self.url = image_url
        self._file_path = ""

    def get_file_path(self):
        if self._file_path == "":
            try:
                os.mkdir('./cache/templates')
            except FileExistsError:
                pass
            self._file_path = f"./cache/templates/{self.id}-meme.jpg"

            response = requests.get(self.url)
            with open(self._file_path, 'wb') as f:
                f.write(response.content)
                f.close()
        return self._file_path

    def get_box_count(self):
        return self.box_count


class MemeViewWindow(Screen):
    Meme = None

    def __init__(self, **kwargs):
        super(MemeViewWindow, self).__init__(**kwargs)
        self.cols = 1
        self.rows = 2
        self.meme_image = AsyncImage(source="", size_hint=(1, 1), allow_stretch=True)
        self.back_button = Button(text="Back", size_hint=(0.1, 0.1))
        self.back_button.bind(on_press=self.back_button_pressed)
        self.add_widget(self.meme_image)
        self.add_widget(self.back_button)

    @staticmethod
    def back_button_pressed(*_):
        RunApp.ScreenManager.current = "main"

    def set_meme(self, meme: MemeClass):
        self.Meme = meme
        self.meme_image.source = meme.get_file_path()


class TemplateBuilderWindow(GridLayout):
    Template = None

    def __init__(self, **kwargs):
        super(TemplateBuilderWindow, self).__init__(**kwargs)
        self.cols = 1
        self.rows = 2
        self.Image = AsyncImage(size_hint=(1, 1), allow_stretch=True, source="")
        self.bottom_layout = None
        self.continue_button = None
        self.inputs = []

    def set_template(self, template: TemplateMeme):
        self.Template = template
        self.Image.source = template.get_file_path()

        boxes = 2 if template.get_box_count() > 2 else template.get_box_count()

        self.bottom_layout = GridLayout(cols=(boxes * 2) + 1, rows=1, size_hint=(1, .05))
        self.continue_button = Button(text="Enter", size_hint=(.2, 1), on_press=self.continue_button_pressed)
        self.inputs = []
        for i in range(boxes):
            temp_l = Label(text=f"Box {i + 1}", size_hint=(.2, 1))
            temp_i = TextInput(password=False)
            self.inputs.append(temp_i)
            self.bottom_layout.add_widget(temp_l)
            self.bottom_layout.add_widget(temp_i)
        self.bottom_layout.add_widget(self.continue_button)
        self.add_widget(self.Image)
        self.add_widget(self.bottom_layout)

    def continue_button_pressed(self, *_):

        self.remove_widget(self.bottom_layout)
        self.remove_widget(self.Image)

        username = RunApp.config.items('security')[0][1]
        password = RunApp.config.items('security')[1][1]

        if username == "" or password == "":
            Logger.warn("Username or password is empty")
            username = None
            password = None

        top_text = self.inputs[0].text
        if len(self.inputs) > 1:
            bottom_text = self.inputs[1].text
        else:
            bottom_text = ""
        response = caption_meme(self.Template.id, top_text, bottom_text, username, password)
        if response["success"]:
            meme = MemeClass(self.Template.id, top_text, bottom_text, self.Template.get_box_count(), response['data']["url"])
            RunApp.MemeViewWindow.set_meme(meme)
            RunApp.ScreenManager.current = "meme_view"
        else:
            Logger.error(response["error_message"])
            RunApp.InfoWindow.Next = "main"
            RunApp.InfoWindow.update_info(response["error_message"])
            RunApp.ScreenManager.current = "info"


class MainWindow(GridLayout):
    def __init__(self, **kwargs):
        super(MainWindow, self).__init__(**kwargs)
        self.pointer = -1
        self.templates = RunApp.Templates
        self.rows = 3
        self.top_row = GridLayout(cols=3, rows=1, size_hint=(1, .1))
        self.button_layout = GridLayout(cols=3, rows=1, size_hint=(1, .05))

        self.settings_button = Button(text="Settings", size_hint=(.5, 1), on_press=self.settings_button_pressed)
        self.top_row.add_widget(self.settings_button)
        self.top_row.add_widget(Label())  # spacer
        self.top_row.add_widget(Label())
        self.add_widget(self.top_row)

        self.ImageView = AsyncImage(source='./cache/default.jpg', allow_stretch=True)
        self.ImageView.bind(on_error=self.on_error)
        self.add_widget(self.ImageView)

        self.right_button = Button(text='Right')
        self.right_button.bind(on_press=self.right_button_clicked)
        self.left_button = Button(text='Left')
        self.left_button.bind(on_press=self.left_button_clicked)
        self.select_button = Button(text='Select')
        self.select_button.bind(on_press=self.select_button_clicked)

        self.button_layout.add_widget(self.left_button)
        self.button_layout.add_widget(self.select_button)
        self.button_layout.add_widget(self.right_button)
        self.add_widget(self.button_layout)
        Window.bind(on_key_down=self.keyboard_on_key_down)

    @staticmethod
    def settings_button_pressed(*_):
        RunApp.open_settings()

    def on_error(self, *args):
        self.ImageView.source = './cache/default.jpg'

    def right_button_clicked(self, *_):
        self.pointer += 1
        if self.pointer >= len(self.templates):
            self.pointer = 0
        self.ImageView.source = self.templates[self.pointer].get_file_path()

    def left_button_clicked(self, *_):
        self.pointer -= 1
        if self.pointer < 0:
            self.pointer = len(self.templates) - 1
        self.ImageView.source = self.templates[self.pointer].get_file_path()

    def select_button_clicked(self, *_):
        RunApp.TemplateBuilderWindow.set_template(self.templates[self.pointer])
        RunApp.ScreenManager.current = 'template_builder'

    def keyboard_on_key_down(self, window, keyboard, keycode, text, modifiers):
        Logger.info(f"Keycode: {keycode}")
        if RunApp.ScreenManager.current == 'main':
            if int(keycode) == WindowsKeyboard.RIGHT_ARROW.value:
                self.right_button_clicked()
            elif int(keycode) == WindowsKeyboard.LEFT_ARROW.value:
                self.left_button_clicked()
            elif int(keycode) == WindowsKeyboard.SPACE_BAR.value:
                self.select_button_clicked()


def load_memes() -> typing.List[TemplateMeme]:
    templates = []
    if os.path.exists("./cache/templates/templates.pkl"):
        with open("./cache/templates/templates.pkl", "rb") as f:
            templates = pickle.load(f)
            f.close()
    else:
        for template in tqdm.tqdm(get_memes()["data"]["memes"], desc="Loading templates", unit="templates", unit_scale=True):
            template_id = template['id']
            name = template['name']
            url = template['url']
            width = template['width']
            height = template['height']
            box_count = template['box_count']
            templates.append(TemplateMeme(template_id, name, url, width, height, box_count))
        with open("./cache/templates/templates.pkl", "wb") as f:
            pickle.dump(templates, f)
            f.close()
    return templates


# noinspection PyAttributeOutsideInit
class MemeCreator(App):
    ScreenManager = None
    Templates = []

    def build(self):
        self.config.read('./app/core/config.ini')
        self.ScreenManager = ScreenManager()
        self.MainScreen = Screen(name='main')
        self.TemplateBuilderScreen = Screen(name='template_builder')
        self.MemeViewScreen = Screen(name='meme_view')
        self.InfoScreen = Screen(name='info')

        self.MainWindow = None
        self.TemplateBuilderWindow = None
        self.MemeViewWindow = None
        self.InfoWindow = None

        if not os.path.exists("cache"):
            os.mkdir('cache/')
            os.mkdir('cache/templates')
        elif not os.path.exists("cache/templates"):
            os.mkdir('cache/templates')

        return self.ScreenManager

    def build_settings(self, settings):
        settings.add_json_panel('General', self.config, filename='app/core/panel_one.json')

    def on_start(self):
        self.Templates = load_memes()

        self.MainWindow = MainWindow()
        self.MainScreen.add_widget(self.MainWindow)

        self.TemplateBuilderWindow = TemplateBuilderWindow()
        self.TemplateBuilderScreen.add_widget(self.TemplateBuilderWindow)

        self.MemeViewWindow = MemeViewWindow()
        self.MemeViewScreen.add_widget(self.MemeViewWindow)

        self.InfoWindow = InfoWindow()
        self.InfoScreen.add_widget(self.InfoWindow)

        self.ScreenManager.add_widget(self.MainScreen)
        self.ScreenManager.add_widget(self.TemplateBuilderScreen)
        self.ScreenManager.add_widget(self.MemeViewScreen)
        self.ScreenManager.add_widget(self.InfoScreen)
        self.ScreenManager.current = 'main'


if __name__ == '__main__':
    RunApp = MemeCreator()
    RunApp.run()
