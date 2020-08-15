"""Program for creating flexible schedules"""

from abc import ABC, abstractmethod
from random import randint, choice, shuffle, random
import json
import tkinter as tk
from tkinter import ttk
from os.path import isfile
import xml.etree.ElementTree as ElTr


class Main:
    """Main window of program"""

    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.title("Daily plan creator")
        self.main_window.resizable(0, 0)  # user can't change size of a main window

        data = get_json_data()
        theme = data['theme']
        theme_dict = THEMES[theme]
        # Menu
        self.main_menu = tk.Menu(self.main_window)
        self.main_window.config(menu=self.main_menu)
        self.main_menu.add_command(label=TEXT['work_cycle_config'], command=lambda:
                                   WorkCycleConfigGetter(self, theme_dict).pack())
        self.appearance_menu = tk.Menu(self.main_menu, tearoff=0)
        self.appearance_menu.add_command(label=TEXT["light"],
                                         command=lambda: self.set_theme("light"))
        self.appearance_menu.add_command(label=TEXT["dark"], command=lambda: self.set_theme("dark"))
        self.main_menu.add_cascade(label=TEXT["theme"], menu=self.appearance_menu)
        self.scrollbars_menu = tk.Menu(self.main_menu, tearoff=0)
        self.scrollbars_menu.add_command(label=TEXT["show"], command=self.pack_scrollbars)
        self.scrollbars_menu.add_command(label=TEXT['hide'], command=self.unpack_scrollbars)
        self.main_menu.add_cascade(label=TEXT["scrollbars"], menu=self.scrollbars_menu)
        self.main_menu.add_command(label=TEXT['help'], command=self.display_help)

        self.left_frame = tk.Frame()
        self.pleasures_frame = PleasuresFrame(self, self.left_frame, TEXT['pleasures'])
        self.activities_frame = ActivitiesFrame(self, self.left_frame, TEXT['activities'])

        self.right_frame = tk.Frame()
        self.schedule_frame = ScheduleFrame(self, self.right_frame, TEXT['schedule'])
        self.routines_frame = RoutinesFrame(self, self.right_frame, TEXT['tasks'])

        self.go_button = tk.Button(self.main_window, text=TEXT['create_plan'],
                                   command=self.__make_schedule,
                                   height=1, width=32, font=("Courier", 20))
        self.textbox_frame = tk.Frame(self.main_window)
        self.scrollbar = tk.Scrollbar(self.textbox_frame)
        self.textbox = tk.Text(self.textbox_frame, height=34, width=65,
                               wrap=tk.WORD, font=BUTTON_FONT,
                               yscrollcommand=self.scrollbar.set)
        self.__pack()
        self.set_theme(theme)
        self.main_window.bind_all("<Control-Key>", self.textbox_binds)
        if not data['was_help_shown']:
            self.display_help()
        self.main_window.mainloop()  # this must be the last instruction
        # because it activates the window

    def display_help(self):
        """Show help in the textbox"""
        self.textbox.delete('1.0', tk.END)  # Clear text
        for index in range(1, 9):
            self.textbox.insert(tk.END, TEXT['help_text_{}'.format(index)]+'\n\n')
        write_json_data_by_key(True, "was_help_shown")

    def textbox_binds(self, event):
        """Bind the textbox so you don't need English-keyboard acitvated"""
        if event.keycode == 65:  # a
            self.textbox.tag_add(tk.SEL, "1.0", tk.END)
        elif event.keycode == 67:  # c
            self.textbox.event_generate("<<Copy>>")
        elif event.keycode == 88:  # x
            self.textbox.event_generate("<<Cut>>")
        elif event.keycode == 86:  # v
            self.textbox.event_generate("<<Paste>>")

    def set_theme(self, theme_name: str):
        """Set the theme"""
        theme = THEMES[theme_name]
        write_json_data_by_key(theme_name, "theme")
        self.main_window.configure(bg=theme['window'])
        self.textbox.configure(bg=theme['textbox'], fg=theme['fg'])
        self.go_button.configure(bg=theme['button'], fg=theme['fg'])
        self.main_menu.configure(bg=theme['menu'], fg=theme['fg'])
        self.appearance_menu.configure(bg=theme['menu'], fg=theme['fg'])
        self.scrollbars_menu.configure(bg=theme['menu'], fg=theme['fg'])
        self.schedule_frame.set_theme(theme)
        self.routines_frame.set_theme(theme)
        self.pleasures_frame.set_theme(theme)
        self.activities_frame.set_theme(theme)

    def pack_scrollbars(self):
        """Add all the scrollbars"""
        write_json_data_by_key(True, "show_scrollbars")
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.activities_frame.pack_scrollbar()
        self.pleasures_frame.pack_scrollbar()
        self.routines_frame.pack_scrollbar()
        self.schedule_frame.pack_scrollbar()

    def unpack_scrollbars(self):
        """Remove all the scrollbars"""
        write_json_data_by_key(False, "show_scrollbars")
        self.scrollbar.pack_forget()
        self.activities_frame.unpack_scrollbar()
        self.pleasures_frame.unpack_scrollbar()
        self.routines_frame.unpack_scrollbar()
        self.schedule_frame.unpack_scrollbar()

    def __pack(self):
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.pleasures_frame.pack(tk.TOP, tk.N)
        self.activities_frame.pack(tk.BOTTOM, tk.S)

        self.right_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.schedule_frame.pack(tk.BOTTOM, tk.N)
        self.routines_frame.pack(tk.TOP, tk.S)
        self.go_button.pack(side=tk.BOTTOM, anchor=tk.S)
        self.textbox_frame.pack()
        self.textbox.pack(side=tk.LEFT)
        if get_json_data()['show_scrollbars']:
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def __make_schedule(self):
        """Make a schedule based on options"""
        self.textbox.delete('1.0', tk.END)  # Clear text
        activities = get_json_data()['activities']
        amount_of_activities = self.activities_frame.get_amount_of_activities()
        chosen_activities = choose_activities(activities, amount_of_activities)
        chosen_activities = squeeze_activities_weight(chosen_activities)
        work_blocks = get_json_data()['work_blocks']
        # Distribute routines between work blocks
        routines = list(get_json_data()['routines'].values())
        routines.sort(key=lambda x: len(x['active_work_blocks']))
        for _ in range(100):  # 100 trials of distribution
            for work_block in work_blocks:
                # Create a space in work block for routine entries (and clear it)
                work_block['routines'] = []
                work_block['time_left'] = work_block['duration']  # time in work block
            for routine in routines:
                active_work_blocks = routine['active_work_blocks']
                if active_work_blocks:
                    index = choice(active_work_blocks)
                    work_block = dict(work_blocks[index])
                    work_block['routines'].append(routine)
                    work_block['time_left'] -= routine['duration']
                    work_blocks[index] = work_block
            # if work block duration is not exceeded by routines,
            # then distribution completed successfully
            if all(work_block['time_left'] >= 0 for work_block in work_blocks):
                break
            else:
                continue
        else:  # So after 100 trial distribution still failed
            self.textbox.insert(tk.END, TEXT['failed_to_create'])
            return  # Stop the function

        schedule_list = get_json_data()['schedule'] + work_blocks
        schedule_list.sort(key=lambda x: x['start'])
        for schedule_paragraph in schedule_list:
            end_minute = schedule_paragraph['end']
            start_minute = schedule_paragraph['start']
            if 'duration' in schedule_paragraph.keys():  # work block
                self.insert_work_block(schedule_paragraph, start_minute,
                                       end_minute, chosen_activities)
            else:  # just a paragraph
                self.insert_paragraph(schedule_paragraph, start_minute, end_minute)
        for pleasure in get_json_data()['pleasures'].values():
            if random() * 100 > pleasure['probability']:
                self.textbox.insert(tk.END, TEXT['pleasure_forbidden'].format(
                    pleasure['name'])+'\n')

    def insert_paragraph(self, schedule_paragraph, start_minute, end_minute):
        """Insert paragraph data to textbox"""
        name = schedule_paragraph['name']
        start_str = minutes_to_time(start_minute)
        if start_minute != end_minute:
            end_str = minutes_to_time(end_minute)
            self.textbox.insert(tk.END, "{} - {} {}\n".format(start_str, end_str, name))
        else:
            self.textbox.insert(tk.END, "{} {}\n".format(start_str, name))

    def insert_work_block(self, schedule_paragraph, start_minute, end_minute, activities):
        """Insert work block data to textbox"""
        # Preparing variables
        data = get_json_data()
        min_time = data["work_cycle_min_time"]
        max_time = data["work_cycle_max_time"]
        activities = dict(activities)
        minutes_of_work = schedule_paragraph['duration']
        sequence = schedule_paragraph['routines']
        minutes_of_rest = end_minute - start_minute - minutes_of_work

        for routine in sequence:
            minutes_of_work -= routine['duration']
        while minutes_of_work >= min_time:
            name = TEXT["work_cycle"]
            if activities:
                activity = choose_one_activity(activities)["name"]
                name += ' [{}]'.format(activity)
            time_block = choice(range(min_time, min(max_time, minutes_of_work) + 1, 5))
            sequence.append({'name': name, 'duration': time_block})
            minutes_of_work -= time_block
        minutes_of_rest += minutes_of_work
        shuffle(sequence)
        sequence.append({'name': TEXT['rest'], 'duration': minutes_of_rest})

        for paragraph in sequence:
            start_str = minutes_to_time(start_minute)
            name = paragraph['name']
            if paragraph['duration'] == 0:
                self.textbox.insert(tk.END, "{} {}\n".format(start_str, name))
            else:
                # we created start_str so we can change start_minute
                start_minute += paragraph['duration']
                end_str = minutes_to_time(start_minute)
                self.textbox.insert(tk.END, "{} - {} {}\n".format(start_str, end_str, name))


class LanguageGetter:
    """Window to get the language"""

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Choose language")
        self.russian_button = tk.Button(self.window,
                                        text="Русский", command=lambda: self.choose_russian(),
                                        width=10, height=1, font=("Courier", 48))
        self.english_button = tk.Button(self.window,
                                        text="English", command=lambda: self.choose_english(),
                                        width=10, height=1, font=("Courier", 48))
        self.chosen_language = None

    def pack(self):
        self.english_button.pack()
        self.russian_button.pack()
        self.window.mainloop()
        return self.chosen_language

    def choose_russian(self):
        self.chosen_language = 'russian'
        self.window.destroy()

    def choose_english(self):
        self.chosen_language = 'english'
        self.window.destroy()


class Frame(ABC):
    """A frame with listbox and buttons"""

    def __init__(self, main: Main, master, name: str):
        self.name = name
        self.main = main
        self.frame = tk.LabelFrame(master, text=name)
        self.listbox_scrollbar_frame = tk.Frame(self.frame)
        self.scrollbar = tk.Scrollbar(self.listbox_scrollbar_frame)
        self.listbox = tk.Listbox(self.listbox_scrollbar_frame,
                                  width=48, height=14, font=BUTTON_FONT,
                                  yscrollcommand=self.scrollbar.set)
        self.redact_button = None
        self.delete_button = None
        self.bottom_button_frame = tk.Frame(self.frame)
        self.top_button_frame = tk.Frame(self.frame)
        self.theme = None

    @abstractmethod
    def pack(self, side, anchor):
        """Pack the frame"""
        self.fill_listbox()
        self.frame.pack(side=side, anchor=anchor, fill=tk.BOTH)
        self.listbox_scrollbar_frame.pack(side=tk.TOP)
        self.listbox.pack(side=tk.LEFT)
        if get_json_data()["show_scrollbars"]:
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.top_button_frame.pack()
        self.bottom_button_frame.pack()

    @abstractmethod
    def fill_listbox(self):
        """Fill the listbox"""

    def update(self):
        """Clear and fill listbox again"""
        self.listbox.delete(0, tk.END)
        self.fill_listbox()

    def activate_disabled_buttons(self):
        """Enable redact and delete buttons"""
        self.redact_button.configure(state=tk.NORMAL)
        self.delete_button.configure(state=tk.NORMAL)

    def disable_buttons(self):
        """Disable redact and delete buttons"""
        self.redact_button.configure(state=tk.DISABLED)
        self.delete_button.configure(state=tk.DISABLED)

    def set_theme(self, theme: dict):
        """Set the theme in the frame"""
        self.theme = theme
        self.frame.configure(bg=theme['frame'], fg=theme['fg'])
        self.listbox.configure(bg=theme['listbox'], fg=theme['fg'])
        for slave in self.bottom_button_frame.pack_slaves() + self.top_button_frame.pack_slaves():
            slave.configure(bg=theme['button'], fg=theme['fg'])

    def pack_scrollbar(self):
        """Add the scrollbar"""
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def unpack_scrollbar(self):
        """Remove the scrollbar"""
        self.scrollbar.pack_forget()


class PleasuresFrame(Frame):
    """Frame with pleasures"""

    def pack(self, side, anchor):
        """Pack the frame"""
        super().pack(side, anchor)
        self.listbox.bind("<Button-1>", lambda _: self.activate_disabled_buttons())
        add_pleasure = tk.Button(self.bottom_button_frame, text=TEXT['add_pleasure'],
                                 command=lambda: PleasureGetter(self.main, self.theme).pack(),
                                 font=BUTTON_FONT, width=15)
        self.redact_button = tk.Button(self.bottom_button_frame,
                                       text=TEXT["redact"], state=tk.DISABLED,
                                       command=self.change_pleasure_window,
                                       font=BUTTON_FONT, width=15)
        self.delete_button = tk.Button(self.bottom_button_frame,
                                       text=TEXT["delete"], state=tk.DISABLED,
                                       command=self.delete_pleasure, font=BUTTON_FONT, width=15)
        add_pleasure.pack(side=tk.LEFT)
        self.redact_button.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.LEFT)

    def fill_listbox(self):
        """Fill the listbox with pleasures"""
        pleasures_dictionary = get_json_data()['pleasures']
        for pleasure in pleasures_dictionary:
            pleasure_object = Pleasure(pleasures_dictionary[pleasure])
            self.listbox.insert(tk.END, pleasure_object.get_string())

    def change_pleasure_window(self):
        """Redact a pleasure"""
        dictionary = create_pleasure_dict_by_string(self.listbox.get(tk.ACTIVE))
        PleasureGetter(self.main, self.theme, **dictionary).pack()

    def delete_pleasure(self):
        """Delete a pleasure"""
        data = get_json_data()
        dictionary = create_pleasure_dict_by_string(self.listbox.get(tk.ACTIVE))
        self.listbox.delete(tk.ACTIVE)
        self.disable_buttons()
        data['pleasures'].pop(dictionary['name'])
        write_json_data(data)


class ScheduleFrame(Frame):
    """Frame for schedule, with work blocks and paragraphs"""

    def pack(self, side, anchor):
        """Create schedule frame"""
        super().pack(side, anchor)
        self.listbox.bind("<Button-1>", lambda _: self.activate_disabled_buttons())
        self.redact_button = tk.Button(self.bottom_button_frame,
                                       text=TEXT["redact"], state=tk.DISABLED,
                                       command=self.redact_schedule, font=BUTTON_FONT, width=23)
        self.delete_button = tk.Button(self.bottom_button_frame,
                                       text=TEXT['delete'], state=tk.DISABLED,
                                       command=self.delete_paragraph_or_work_block,
                                       font=BUTTON_FONT, width=23)
        add_schedule_paragraph = tk.Button(self.top_button_frame,
                                           text=TEXT['add_paragraph'], width=23,
                                           command=lambda: ParagraphGetter(self.main,
                                                                           self.theme).pack(),
                                           font=BUTTON_FONT)
        add_work_block = tk.Button(self.top_button_frame, text=TEXT['add_work_block'], width=23,
                                   command=lambda: WorkBlockGetter(self.main, self.theme).pack(),
                                   font=BUTTON_FONT)
        add_schedule_paragraph.pack(side=tk.LEFT)
        add_work_block.pack(side=tk.LEFT)
        self.redact_button.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.LEFT)

    def fill_listbox(self):
        """Fill the listboxs with work blocks and paragraphs"""
        data = get_json_data()
        schedule_list = data['schedule'] + data['work_blocks']
        schedule_list.sort(key=lambda x: x['start'])
        for paragraph in schedule_list:
            if 'duration' in paragraph.keys():
                work_block = WorkBlock(paragraph)
                self.listbox.insert(tk.END, work_block.get_string())
            else:
                paragraph = Paragraph(paragraph)
                self.listbox.insert(tk.END, paragraph.get_string())

    def redact_schedule(self):
        """Redact a paragraph or a work block"""
        dictionary = create_work_block_or_paragraph_dict_by_string(self.listbox.get(tk.ACTIVE))
        if 'duration' in dictionary:
            WorkBlockGetter(self.main, self.theme, **dictionary).pack()
        else:
            ParagraphGetter(self.main, self.theme, **dictionary).pack()

    def delete_paragraph_or_work_block(self):
        """Delete a paragraph or a work block"""
        data = get_json_data()
        dictionary = create_work_block_or_paragraph_dict_by_string(self.listbox.get(tk.ACTIVE))
        self.listbox.delete(tk.ACTIVE)
        self.disable_buttons()
        if 'duration' in dictionary:
            data['work_blocks'].remove(dictionary)
            write_json_data(data)
            self.main.routines_frame.clear_active_work_blocks()
        else:
            data['schedule'].remove(dictionary)
            write_json_data(data)


class RoutinesFrame(Frame):
    """Frame with routines"""
    def pack(self, side, anchor):
        super().pack(side, anchor)
        self.listbox.bind("<Button-1>", lambda _: self.activate_disabled_buttons())
        self.redact_button = tk.Button(self.bottom_button_frame,
                                       text=TEXT["redact"], state=tk.DISABLED,
                                       command=self.redact_routine, font=BUTTON_FONT, width=15)
        self.delete_button = tk.Button(self.bottom_button_frame,
                                       text=TEXT['delete'], state=tk.DISABLED,
                                       command=self.delete_routine, font=BUTTON_FONT, width=15)
        add_routine = tk.Button(self.bottom_button_frame, text=TEXT['add_task'], width=15,
                                command=lambda: RoutineGetter(self.main, self.theme).pack(),
                                font=BUTTON_FONT)
        add_routine.pack(side=tk.LEFT)
        self.redact_button.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.LEFT)

    def fill_listbox(self):
        """Fill the listbox with routines"""
        routines_dict = get_json_data()['routines']
        for routine in routines_dict.keys():
            self.listbox.insert(tk.END, Routine(routines_dict[routine]).get_string())

    def redact_routine(self):
        """Redact a routine"""
        dictionary = create_routine_dict_by_string(self.listbox.get(tk.ACTIVE))
        RoutineGetter(self.main, self.theme, **dictionary).pack()

    def delete_routine(self):
        """Delete a routine"""
        data = get_json_data()
        dictionary = create_routine_dict_by_string(self.listbox.get(tk.ACTIVE))
        self.listbox.delete(tk.ACTIVE)
        self.disable_buttons()
        data['routines'].pop(dictionary['name'])
        write_json_data(data)

    def clear_active_work_blocks(self):
        """Made active_work_blocks field blank in all routines"""
        data = get_json_data()
        for routine in data['routines']:
            data['routines'][routine]['active_work_blocks'] = []
        write_json_data(data)
        self.update()


class ActivitiesFrame(Frame):
    """Frame with activities"""

    def __init__(self, main: Main, master, name: str):
        super().__init__(main, master, name)
        self.listbox.bind("<Button-1>", lambda _: self.activate_disabled_buttons())
        self.activities_number_frame = tk.Frame(self.frame)
        self.activities_number_label = tk.Label(self.activities_number_frame, font=BUTTON_FONT,
                                                text=TEXT["how_many_activities"])
        self.activities_number_variable = tk.IntVar(value=get_json_data()['activities_number'])
        values = list(range(len(get_json_data()['activities']) + 1))
        self.activities_number_combobox = ttk.Combobox(self.activities_number_frame, width=2,
                                                       values=values, font=BUTTON_FONT,
                                                       textvariable=self.activities_number_variable)
        self.activities_number_variable.trace('w', lambda *_: self.update_activities_number())
        self.activities_number_combobox.current(get_json_data()['activities_number'])
        self.add_button = tk.Button(self.bottom_button_frame, text=TEXT['add_activity'], width=15,
                                    command=lambda: ActivityGetter(self.main, self.theme).pack(),
                                    font=BUTTON_FONT)
        self.redact_button = tk.Button(self.bottom_button_frame,
                                       text=TEXT['redact'], state=tk.DISABLED,
                                       command=self.redact_activity, font=BUTTON_FONT, width=15)
        self.delete_button = tk.Button(self.bottom_button_frame,
                                       text=TEXT['delete'], state=tk.DISABLED,
                                       command=self.delete_activity, font=BUTTON_FONT, width=15)

    def set_theme(self, theme: dict):
        super().set_theme(theme)
        self.activities_number_label.configure(bg=theme['label'], fg=theme['fg'])

    def update_combobox(self):
        """Update the combobox of possible activities numbers"""
        values = list(range(len(get_json_data()['activities']) + 1))
        self.activities_number_combobox['values'] = values
        if self.activities_number_variable.get() > values[-1]:  # not in range
            self.activities_number_combobox.set(values[-1])

    def get_amount_of_activities(self) -> int:
        """Get the amount of activities that will be in a plan"""
        return int(self.activities_number_combobox.get())

    def pack(self, side, anchor):
        super().pack(side, anchor)
        self.activities_number_frame.pack()
        self.activities_number_label.pack(side=tk.LEFT)
        self.activities_number_combobox.pack(side=tk.RIGHT)
        self.add_button.pack(side=tk.LEFT)
        self.redact_button.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.LEFT)

    def fill_listbox(self):
        """Fill the listbox with activities"""
        activities_dict = get_json_data()['activities']
        for activity in activities_dict.keys():
            self.listbox.insert(tk.END, Activity(activities_dict[activity]).get_string())

    def redact_activity(self):
        """Redact the activity"""
        dictionary = create_activity_dict_by_string(self.listbox.get(tk.ACTIVE))
        ActivityGetter(self.main, self.theme, **dictionary).pack()

    def delete_activity(self):
        """Delete the activity"""
        data = get_json_data()
        dictionary = create_activity_dict_by_string(self.listbox.get(tk.ACTIVE))
        self.listbox.delete(tk.ACTIVE)
        self.disable_buttons()
        data['activities'].pop(dictionary['name'])
        write_json_data(data)
        self.update_combobox()

    def update_activities_number(self):
        """Update the number of activities that will be in plan"""
        write_json_data_by_key(self.activities_number_variable.get(), 'activities_number')


class ObjectFrame(ABC):
    """One object in some frame"""

    @abstractmethod
    def get_string(self):
        """Get the string with info about this object"""


class Routine(ObjectFrame):
    """Some thing that sometimes should be done, like sports or cleaning"""

    def __init__(self, dictionary):
        self.name = dictionary["name"]
        self.duration = dictionary["duration"]
        self.active_work_blocks = dictionary["active_work_blocks"]

    def get_string(self) -> str:
        pluses_minuses = ''
        for index in range(len(get_json_data()['work_blocks'])):
            if index in self.active_work_blocks:
                pluses_minuses += '+'
            else:
                pluses_minuses += '-'
        return "{:30s}[{}] {}".format(self.name, minutes_to_duration(self.duration), pluses_minuses)


class Pleasure(ObjectFrame):
    """Pleasure which can be forbidden for the sake of dopamine quality"""

    def __init__(self, dictionary: dict):
        self.name = dictionary['name']
        self.probability = dictionary['probability']

    def get_string(self):
        return "{:44s} {:2d}%".format(self.name, self.probability)


class Paragraph(ObjectFrame):
    """Paragraph of schedule"""

    def __init__(self, dictionary):
        self.name = dictionary["name"]
        self.start = dictionary["start"]
        self.end = dictionary["end"]

    def get_string(self) -> str:
        """Get string with paragraph info"""
        start_str = minutes_to_time(self.start)
        if self.start != self.end:
            end_str = minutes_to_time(self.end)
            return "{} - {} {}".format(start_str, end_str, self.name)
        return "{} {}".format(start_str, self.name)


class WorkBlock(ObjectFrame):
    """
    Work block
    schedule paragraph which will be randomly filled with routines and work times"""

    def __init__(self, dictionary):
        self.start = dictionary['start']
        self.end = dictionary['end']
        self.duration = dictionary['duration']

    def get_string(self) -> str:
        """Get a string with work block info"""
        duration = minutes_to_duration(self.duration)
        start_str = minutes_to_time(self.start)
        if self.start != self.end:
            end_str = minutes_to_time(self.end)
            return "{} - {} {} [{}]".format(start_str, end_str, TEXT['work_block'], duration)
        return "{} {} [{}]".format(start_str, TEXT['work_block'], duration)


class Activity(ObjectFrame):
    """Activity in ActivitiesFrame"""

    def __init__(self, dictionary):
        self.name = dictionary["name"]
        self.weight = dictionary["weight"]

    def get_string(self) -> str:
        return "{:44s} {:3d}".format(self.name, self.weight)


class SimpleGetter(ABC):
    """Frame to get some data like name or time"""
    def __init__(self, window, theme: dict):
        self.frame = tk.Frame(window, bg=theme["frame"])

    @abstractmethod
    def pack(self):
        """Pack this SimpleGetter in some ObjectGetter"""

    @abstractmethod
    def get(self):
        """Get the data this Getter is responsible for"""


class NameGetter(SimpleGetter):
    """Entry for name of something"""

    def __init__(self, window, theme: dict, name=''):
        super().__init__(window, theme)
        self.name_label = tk.Label(self.frame, text=TEXT['name'], fg=theme['fg'],
                                   bg=theme['label'], font=BUTTON_FONT)
        self.name_entry = tk.Entry(self.frame, bg=theme['entry'],
                                   fg=theme['entry_fg'], font=BUTTON_FONT)
        if name:
            self.name_entry.insert(tk.END, name)

    def pack(self):
        """Pack the frame"""
        self.frame.pack()
        self.name_label.pack(side=tk.LEFT)
        self.name_entry.pack(side=tk.LEFT)

    def get(self):
        """Get the name"""
        return self.name_entry.get()


class TimeGetter(SimpleGetter):
    """Entry for time of something"""

    def __init__(self, window, theme: dict, text, after_midnight_check: bool, time=0):
        super().__init__(window, theme)
        self.after_midnight_check = after_midnight_check
        self.start_observers = []
        self.end_observers = []
        self.theme = theme
        self.minutes = tk.IntVar(master=window, value=time % 60)
        self.hours = tk.IntVar(master=window, value=(time // 60) % 24)
        self.after_midnight = tk.IntVar(master=window, value=time // 1440 * 1440)
        minutes_list = list(range(0, 60, 5))
        hours_list = list(range(0, 24))
        self.label = tk.Label(self.frame, text=text, fg=theme['fg'],
                              bg=theme['label'], font=BUTTON_FONT)
        self.hours_entry = ttk.Combobox(self.frame, values=hours_list,
                                        width=2, font=BUTTON_FONT,
                                        textvariable=self.hours)
        self.hours_entry.current(hours_list.index(self.hours.get()))
        # choose zero as a default hour

        self.minutes_entry = ttk.Combobox(self.frame, values=minutes_list,
                                          width=2, font=BUTTON_FONT,
                                          textvariable=self.minutes)
        self.minutes_entry.current(minutes_list.index(self.minutes.get()))
        # choose zero as a default minute

        self.checkbox = tk.Checkbutton(self.frame, onvalue=1440,
                                       offvalue=0, var=self.after_midnight,
                                       bg=theme["label"], fg=theme["entry_fg"])
        self.a_m_label = tk.Label(self.frame, text=TEXT["after_midnight"],
                                  bg=theme["label"], fg=theme["fg"])

        self.minutes.trace('w', lambda *_: self.update())
        self.hours.trace('w', lambda *_: self.update())
        self.after_midnight.trace('w', lambda *_: self.update())

    def pack(self):
        """Pack frame"""
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.hours_entry.pack(side=tk.LEFT)
        tk.Label(self.frame, text=':', bg=self.theme["label"], fg=self.theme["fg"],
                 font=BUTTON_FONT).pack(side=tk.LEFT)
        self.minutes_entry.pack(side=tk.LEFT)
        if self.after_midnight_check:
            self.checkbox.pack(side=tk.LEFT)
            self.a_m_label.pack(side=tk.LEFT)

    def get(self):
        """Get time"""
        hours = int(self.hours_entry.get())
        minutes = int(self.minutes_entry.get())
        return hours * 60 + minutes + self.after_midnight.get()

    def register_start_observer(self, observer):
        """Add an observer for which's event this time is start"""
        self.start_observers.append(observer)

    def register_end_observer(self, observer):
        """Add an observer for which's event this time is end"""
        self.end_observers.append(observer)

    def update(self):
        """Update observers"""
        for observer in self.start_observers:
            observer.update_start(self.get())
        for observer in self.end_observers:
            observer.update_end(self.get())


class NumberGetter(SimpleGetter):
    """Entry for getting a number"""
    def __init__(self, window, theme: dict, text, default_number=''):
        super().__init__(window, theme)
        self.label = tk.Label(self.frame, text=text, fg=theme['fg'],
                              bg=theme['label'], font=BUTTON_FONT)
        self.duration_entry = tk.Entry(self.frame, width=3, fg=theme['entry_fg'],
                                       bg=theme['entry'], font=BUTTON_FONT)
        if default_number:
            self.duration_entry.insert(tk.END, default_number)

    def pack(self):
        """Pack a frame"""
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.duration_entry.pack(side=tk.LEFT)

    def get(self):
        """Get number"""
        return int(self.duration_entry.get())

    def inputed_correctly(self):
        """Checks if number inputed correctly"""
        return self.duration_entry.get().isdigit()


class ObjectGetter(ABC):
    """Window with entries for objects like pleasures and work blocks"""

    def __init__(self, master: Main, theme: dict):
        self.master = master
        self.window = tk.Tk()
        self.okay_button = tk.Button(self.window, text="OK", font=BUTTON_FONT,
                                     command=self.append_to_json,
                                     fg=theme['fg'], bg=theme['button'])
        self.error_label = tk.Label(self.window, fg='red', bg=theme['label'], font=BUTTON_FONT)
        self.window.configure(bg=theme['window'])

    @abstractmethod
    def pack(self):
        """Create a window with entries"""
        self.error_label.pack()
        self.okay_button.pack()
        self.window.mainloop()

    @abstractmethod
    def append_to_json(self):
        """Append data about object to json-file"""


class WorkCycleConfigGetter(ObjectGetter):
    """Window to configure work blocks"""

    def __init__(self, master: Main, theme: dict):
        super().__init__(master, theme)
        data = get_json_data()
        self.min_time = TimeGetter(self.window, theme, TEXT["min_time"], False,
                                   data['work_cycle_min_time'])
        self.max_time = TimeGetter(self.window, theme, TEXT["max_time"], False,
                                   data['work_cycle_max_time'])

    def pack(self):
        self.min_time.pack()
        self.max_time.pack()
        super().pack()

    def append_to_json(self):
        if self.min_time.get() > self.max_time.get():
            self.error_label['text'] = TEXT["min_and_max_time_error"]
        else:
            data = get_json_data()
            data['work_cycle_min_time'] = self.min_time.get()
            data['work_cycle_max_time'] = self.max_time.get()
            write_json_data(data)
            self.window.destroy()


class PleasureGetter(ObjectGetter):
    """Window with entries for pleasure"""

    def __init__(self, master: Main, theme: dict, name='', probability=''):
        super().__init__(master, theme)
        self.name_frame = NameGetter(self.window, theme, name=name)
        self.probability = NumberGetter(self.window, theme, TEXT['probability'], probability)
        self.old_name = name

    def pack(self):
        self.name_frame.pack()
        self.probability.pack()
        super().pack()

    def append_to_json(self):
        """Write data about pleasure to json"""
        if self.probability.inputed_correctly():
            paragraph = self.paragraph()
            data = get_json_data()
            if self.old_name in data['pleasures']:
                data['pleasures'].pop(self.old_name)
            data['pleasures'][self.name()] = paragraph
            write_json_data(data)
            self.master.pleasures_frame.update()
            self.window.destroy()
        else:
            self.error_label["text"] = TEXT["number_input_error"]

    def paragraph(self) -> dict:
        """Get data about pleasure as dictionary"""
        return {'name': self.name_frame.get(), 'probability': self.probability.get()}

    def name(self):
        """Get pleasure's name"""
        return self.name_frame.get()


class ParagraphGetter(ObjectGetter):
    """Window with entries for schedule paragraph"""

    def __init__(self, master: Main, theme: dict, name='', start=0, end=0):
        super().__init__(master, theme)
        self.old_paragraph = {"name": name, "start": start, "end": end}
        self.name_frame = NameGetter(self.window, theme, name=name)
        self.start_frame = TimeGetter(self.window, theme, TEXT['start'], True, time=start)
        self.end_frame = TimeGetter(self.window, theme, TEXT['end'], True, time=end)

        self.duration_label = DurationLabel(self.window, theme, start, end)
        self.start_frame.register_start_observer(self.duration_label)
        self.end_frame.register_end_observer(self.duration_label)

    def pack(self):
        """Create a window and run it"""
        self.name_frame.pack()
        self.start_frame.pack()
        self.end_frame.pack()
        self.duration_label.pack()
        super().pack()

    def append_to_json(self):
        """Write data about schedule paragraph into json"""
        if TEXT["work_block"] in self.name_frame.get():
            self.error_label["text"] = TEXT["work_block_in_name_error"]
        elif self.end_frame.get() < self.start_frame.get():
            self.error_label["text"] = TEXT["start_and_end_time_error"]
        elif self.end_frame.get() - self.start_frame.get() >= 1440:
            self.error_label["text"] = TEXT["too_long_error"]
        else:
            paragraph = self.paragraph()
            data = get_json_data()
            if self.old_paragraph in data['schedule']:
                data['schedule'].remove(self.old_paragraph)
            data['schedule'].append(paragraph)
            write_json_data(data)
            self.master.schedule_frame.update()
            self.window.destroy()

    def paragraph(self) -> dict:
        """Get paragraph properties as dictionary"""
        return {"name": self.name_frame.get(),
                "start": self.start_frame.get(),
                "end": self.end_frame.get()}


class RoutineGetter(ObjectGetter):
    """Window with entries for routine to create or update one"""

    def __init__(self, master: Main, theme: dict, name='', duration=0, active_work_blocks=None):
        super().__init__(master, theme)
        if active_work_blocks is None:
            active_work_blocks = []
        self.name_frame = NameGetter(self.window, theme, name=name)
        self.duration_frame = TimeGetter(self.window, theme, TEXT['duration'], False, time=duration)
        self.active_work_blocks = active_work_blocks

        self.bottom_frame = tk.Frame(self.window)
        self.off_frame = tk.LabelFrame(self.bottom_frame, text=TEXT["won't_get_in"],
                                       bg=theme["frame"], fg=theme["fg"])
        self.off_listbox = tk.Listbox(self.off_frame, width=40, bg=theme["listbox"],
                                      fg=theme["fg"], font=BUTTON_FONT)

        self.on_frame = tk.LabelFrame(self.bottom_frame, text=TEXT['will_get_in'],
                                      bg=theme["frame"], fg=theme["fg"])
        self.on_listbox = tk.Listbox(self.on_frame, width=40, bg=theme["listbox"],
                                     fg=theme["fg"], font=BUTTON_FONT)

        self.old_name = name

    def pack(self):
        """Create a new window and run it"""
        self.name_frame.pack()
        self.duration_frame.pack()
        self.bottom_frame.pack(side=tk.TOP)
        self.off_frame.pack(side=tk.LEFT)
        self.off_listbox.pack()
        self.off_listbox.bind("<Button-1>", lambda _: self.from_off_listbox_to_on())
        self.on_frame.pack(side=tk.RIGHT)
        self.on_listbox.pack()
        self.on_listbox.bind("<Button-1>", lambda _: self.from_on_listbox_to_off())
        self.fill_listboxes()
        super().pack()

    def append_to_json(self):
        """Write data about routine to json"""
        paragraph = self.paragraph()
        data = get_json_data()
        if self.old_name in data['routines']:
            data['routines'].pop(self.old_name)
        data['routines'][self.name()] = paragraph
        write_json_data(data)
        self.master.routines_frame.update()
        self.window.destroy()

    def paragraph(self) -> dict:
        """Get routine properties as dictionary"""
        return {"name": self.name(),
                "duration": self.duration_frame.get(),
                "active_work_blocks": self.active_work_blocks}

    def fill_listboxes(self):
        """Fill listboxes"""
        work_blocks = get_json_data()['work_blocks']
        index = 0
        for work_block in work_blocks:
            work_block_object = WorkBlock(work_block)
            work_block_string = '{}. {}'.format(index+1, work_block_object.get_string())
            if index in self.active_work_blocks:
                self.on_listbox.insert(tk.END, work_block_string)
            else:
                self.off_listbox.insert(tk.END, work_block_string)
            index += 1

    def name(self) -> str:
        """Get the name of routine"""
        return self.name_frame.get()

    def from_off_listbox_to_on(self):
        """Move work block from off-listbox to on-listbox"""
        work_block = self.off_listbox.get(tk.ACTIVE)
        if work_block:
            work_block_index = int(work_block.split(sep='.')[0]) - 1
            # '2. 14:30 - 21:00 Work block [03:00]' -> 1

            self.active_work_blocks.append(work_block_index)
            self.off_listbox.delete(tk.ACTIVE)
            self.on_listbox.insert(tk.END, work_block)

    def from_on_listbox_to_off(self):
        """Move work block from on-listbox to off-listbox"""
        work_block = self.on_listbox.get(tk.ACTIVE)
        if work_block:
            work_block_index = int(work_block.split(sep='.')[0]) - 1
            # '2. 14:30 - 21:00 Work block [03:00]' -> 1

            self.active_work_blocks.remove(work_block_index)
            self.on_listbox.delete(tk.ACTIVE)
            self.off_listbox.insert(tk.END, work_block)


class WorkBlockGetter(ObjectGetter):
    """Window with entries for work block"""

    def __init__(self, master: Main, theme: dict, start=0, end=0, duration=0):
        super().__init__(master, theme)
        self.old_work_block = {"start": start, "end": end, "duration": duration}
        self.start_frame = TimeGetter(self.window, theme, TEXT['start'], True, time=start)
        self.end_frame = TimeGetter(self.window, theme, TEXT['end'], True, time=end)
        self.duration_frame = TimeGetter(self.window, theme, TEXT['work_duration'], False,
                                         time=duration)

        self.duration_label = DurationLabel(self.window, theme, start, end)
        self.start_frame.register_start_observer(self.duration_label)
        self.end_frame.register_end_observer(self.duration_label)

    def pack(self):
        """Create a new window and run it"""
        self.start_frame.pack()
        self.end_frame.pack()
        self.duration_label.pack()
        self.duration_frame.pack()
        super().pack()

    def append_to_json(self):
        """Write data about work block into json"""
        paragraph = self.paragraph()
        if paragraph['end'] < paragraph['start']:
            self.error_label["text"] = TEXT["start_and_end_time_error"]
        elif paragraph['end'] - paragraph['start'] < paragraph['duration']:
            self.error_label['text'] = TEXT['work_block_duration_error']
        elif paragraph['end'] - paragraph['start'] >= 1440:
            self.error_label['text'] = TEXT['too_long_error']
        else:
            data = get_json_data()
            if self.old_work_block in data['work_blocks']:
                data['work_blocks'].remove(self.old_work_block)
            data['work_blocks'].append(paragraph)
            data['work_blocks'].sort(key=lambda x: x['start'])
            write_json_data(data)
            self.master.schedule_frame.update()
            self.master.routines_frame.update()
            self.window.destroy()

    def paragraph(self) -> dict:
        """Get work block properties as dictionary"""
        return {"start": self.start_frame.get(),
                "end": self.end_frame.get(),
                "duration": self.duration_frame.get()}


class ActivityGetter(ObjectGetter):
    """Window to create or update an activity"""
    def __init__(self, master: Main, theme: dict, name='', weight=''):
        super().__init__(master, theme)
        self.name = name
        self.name_frame = NameGetter(self.window, theme, name=name)
        self.weight = NumberGetter(self.window, theme, TEXT['weight'], weight)

    def pack(self):
        self.name_frame.pack()
        self.weight.pack()
        super().pack()

    def append_to_json(self):
        """Write data about activity to json"""
        if self.weight.inputed_correctly():
            paragraph = self.paragraph()
            data = get_json_data()
            if self.name in data['activities'].keys():  # remove old entry
                data['activities'].pop(self.name)
            data['activities'][self.name_frame.get()] = paragraph
            write_json_data(data)
            self.master.activities_frame.update()
            self.window.destroy()
            self.master.activities_frame.update_combobox()
        else:
            self.error_label["text"] = TEXT["number_input_error"]

    def paragraph(self) -> dict:
        """Get data about activity as dictionary"""
        return {'name': self.name_frame.get(), 'weight': self.weight.get()}


class DurationLabel:
    """Label-observer to monitor start and end time of some event"""

    def __init__(self, master, theme: dict, start_time: int, end_time: int):
        self.start_time = start_time
        self.end_time = end_time
        self.label = tk.Label(master, fg=theme['fg'], bg=theme['label'], font=BUTTON_FONT)
        self._update_label()

    def pack(self):
        """Pack the label"""
        self.label.pack()

    def update_start(self, new_start: int):
        """Update the start time for the event"""
        self.start_time = new_start
        self._update_label()

    def update_end(self, new_end: int):
        """Update the end time of the event"""
        self.end_time = new_end
        self._update_label()

    def _update_label(self):
        duration = self.end_time-self.start_time
        if 0 < duration < 1440:
            self.label['text'] = TEXT['duration:'] + ' ' + minutes_to_duration(duration)
        elif duration == 0:
            self.label['text'] = TEXT['duration:'] + ' ' + TEXT['instant']
        elif duration >= 1440:
            self.label['text'] = TEXT['duration:'] + ' ' + TEXT['too_long']
        else:
            self.label['text'] = TEXT['duration:'] + ' ' + TEXT['negative']


def choose_activities(activities: dict, number: int):
    """Choose activities for the plan"""
    activities = dict(activities)  # this will make sure parameter activities won't be changed
    chosen_activities = dict()
    weight_sum = 0
    for activity in activities.values():
        weight_sum += activity["weight"]
    #  Now we should choose *number* activities
    for _ in range(number):
        weight = randint(1, weight_sum)
        # this logic provides probability #weight/weight_sum# to be chosen for each activity
        for activity in activities:
            if weight <= activities[activity]["weight"]:
                chosen_activities[activity] = activities[activity]
                weight_sum -= activities[activity]["weight"]
                activities.pop(activity)
                break
            weight -= activities[activity]["weight"]
    return chosen_activities


def choose_one_activity(activities):
    """Choose ine activity for a work cycle"""
    activities = dict(activities)  # this will make sure parameter activities won't be changed
    chosen_activity = dict()
    weight_sum = 0
    for activity in activities.values():
        weight_sum += activity["weight"]
    weight = randint(1, weight_sum)
    # this logic provides probability #weight/weight_sum# to be chosen for each activity
    for activity in activities:
        if weight <= activities[activity]["weight"]:
            chosen_activity = activities[activity]
            weight_sum -= activities[activity]["weight"]
            activities.pop(activity)
            break
        weight -= activities[activity]["weight"]
    return chosen_activity


def squeeze_activities_weight(activities: dict) -> dict:
    """Makes activities probability closer to average"""
    activities = dict(activities)  # this will make sure parameter activities won't be changed
    average_weight = 0
    if activities:
        for activity in activities.values():
            average_weight += activity["weight"]
        average_weight //= len(activities)
        for activity in activities:
            activities[activity]["weight"] = \
                (activities[activity]["weight"] + average_weight*2) // 3
    return activities


def minutes_to_time(minutes: int) -> str:
    """Converts minutes to format hh:mm"""
    return f'{(minutes // 60 ) % 24:0>2}:{minutes % 60:0>2}'
    #  %24 is to replace 31:00 with 07:00 of the next day


def minutes_to_duration(minutes: int) -> str:
    """Converts minutes to format hh:mm, but not replaces 31:00 with 07:00"""
    return f'{minutes // 60:0>2}:{minutes % 60:0>2}'


def time_to_minutes(time: str) -> int:
    """Converts format hh:mm to minutes"""
    list_of_numbers = time.split(sep=':')
    return int(list_of_numbers[0])*60 + int(list_of_numbers[1])


def create_pleasure_dict_by_string(string: str) -> dict:
    """Creates a pleasure dict by string"""
    dictionary = dict()
    list_of_words = string.split()
    dictionary["name"] = ' '.join(list_of_words[:-1])  # ['Junk', 'Food', '5%'] -> 'Junk Food'
    dictionary["probability"] = int(list_of_words[-1][:-1])  # ['Junk', 'Food', '5%'] -> 5
    return dictionary


def create_work_block_or_paragraph_dict_by_string(string: str) -> dict:
    """Create dict with work block's or paragraph's keys and values by string"""
    dictionary = dict()
    list_of_words = string.split()
    dictionary['start'] = time_to_minutes(list_of_words[0])
    list_of_words = list_of_words[1:]  # Removing first word which is a start time
    if list_of_words[0] == '-':
        dictionary['end'] = time_to_minutes(list_of_words[1])
        list_of_words = list_of_words[2:]  # Removing '-' and end time
        if dictionary['end'] < dictionary['start']:
            dictionary['end'] += 1440
    else:
        dictionary['end'] = dictionary['start']
    if TEXT['work_block'] in string:
        dictionary['duration'] = time_to_minutes(list_of_words[-1][1:-1])
        # Work block [hh:mm] -> minutes
    else:
        dictionary['name'] = ' '.join(list_of_words)
    return dictionary


def create_routine_dict_by_string(string: str) -> dict:
    """Create dict with routines's keys and values by string"""
    dictionary = dict()
    list_of_words = string.split()
    dictionary['name'] = ' '.join(list_of_words[:-2])
    dictionary['duration'] = time_to_minutes(list_of_words[-2][1:-1])  # 'A B C [01:30] +++' -> 90
    dictionary['active_work_blocks'] = []
    for index in range(len(list_of_words[-1])):
        if list_of_words[-1][index] == '+':
            dictionary['active_work_blocks'].append(index)
    return dictionary


def create_activity_dict_by_string(string: str) -> dict:
    """Create dict with activity's keys and values by string"""
    dictionary = dict()
    list_of_words = string.split()
    dictionary['name'] = ' '.join(list_of_words[:-1])
    dictionary['weight'] = list_of_words[-1]
    return dictionary


def get_json_data():
    """Get all the data from json"""
    with open('data.json', 'r', encoding='utf-8') as file:
        return json.load(file)


def write_json_data(data) -> None:
    """Update the json"""
    with open('data.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def write_json_data_by_key(new_data, key: str) -> None:
    """Update something in json"""
    data = get_json_data()
    data[key] = new_data
    write_json_data(data)


def update_data(default_data):
    """Fill the database with missing keys"""
    data = get_json_data()
    for key in default_data:
        if key not in data.keys():
            data[key] = default_data[key]
    write_json_data(data)


def create_or_update_json_file():
    """Creates json file if absent, else updates so json-file will keep up with upgrades"""
    default_data = {"pleasures": {}, "schedule": [], "work_blocks": [],
                    "routines": {}, "activities": {}, "activities_number": 0,
                    "work_cycle_min_time": 45, "work_cycle_max_time": 120,
                    "language": "", "theme": "light", "show_scrollbars": True,
                    "was_help_shown": False}
    if not isfile("data.json"):
        write_json_data(default_data)
    else:
        update_data(default_data)


def get_language():
    """Get the language"""
    language = get_json_data()["language"]
    if not language:
        language = LanguageGetter().pack()
        data = get_json_data()
        data['language'] = language
        write_json_data(data)
    return language


def get_text(language: str):
    """Get the text dictionary"""
    tree = ElTr.parse('languages/{}.xml'.format(language))
    root = tree.getroot()
    text = dict()
    for child in root:
        text[child.attrib['key']] = child.text
    return text


create_or_update_json_file()
LANGUAGE = get_language()
TEXT = get_text(LANGUAGE)

BUTTON_FONT = ("Courier", 10)

THEMES = dict()
THEMES['light'] = {"textbox": "white", "menu": "#f0f0f0",
                   "button": "#f0f0f0", "window": "#f0f0f0",
                   "frame": "#f0f0f0", "listbox": "white",
                   "label": "#f0f0f0", "entry": "white",
                   "fg": "black", "entry_fg": "black"}
THEMES['dark'] = {"textbox": "#2b2b2b", "menu": "#2b2b2b",
                  "button": "#2b2b2b", "window": "#2b2b2b",
                  "frame": "#2b2b2b", "listbox": "#2b2b2b",
                  "label": "#2b2b2b", "entry": "white",
                  "fg": "#c0c0c0", "entry_fg": "black"}

Main()
