"""Program for creating flexible schedules"""

from abc import ABC, abstractmethod
from random import randint, choice, shuffle, random
import datetime
import json
import tkinter as tk
from tkinter import ttk
from os.path import isfile
from openpyxl import load_workbook


class Main:
    """Main window of program"""

    def __init__(self):
        self.main_window = tk.Tk()
        self.main_window.resizable(0, 0)
        self.pleasures_frame = PleasuresFrame(self, "Удовольствия")
        self.schedule_frame = ScheduleFrame(self, "Расписание")
        self.routines_frame = RoutinesFrame(self, "Дела")
        self.go_button = tk.Button(self.main_window, text='Вперёд!', command=self.__make_schedule,
                                   height=2, width=91)
        self.go_button.pack(side=tk.BOTTOM, anchor=tk.S)
        self.textbox = tk.Text(self.main_window)
        self.textbox.pack()
        self.main_window.mainloop()

    def __make_schedule(self):
        """Make a schedule based on options"""
        self.textbox.delete('1.0', tk.END)
        routines = list(get_routines().values())
        routines.sort(key=lambda x: len(x['active_work_blocks']))
        work_blocks = get_work_blocks()
        for work_block in work_blocks:
            work_block['routines'] = []
        for routine in routines:
            active_work_blocks = routine['active_work_blocks']
            if active_work_blocks:
                index = choice(active_work_blocks)
                work_block = dict(work_blocks[index])
                work_block['routines'].append(routine)
                work_blocks[index] = work_block

        schedule_list = get_schedule() + work_blocks
        schedule_list.sort(key=lambda x: x['start'])
        for schedule_paragraph in schedule_list:
            end_minute = schedule_paragraph['end']
            start_minute = schedule_paragraph['start']
            if 'duration' in schedule_paragraph.keys():  # work block
                self.insert_work_block(schedule_paragraph, start_minute, end_minute)
            else:  # just a paragraph
                self.insert_paragraph(schedule_paragraph, start_minute, end_minute)
        for pleasure in get_pleasures().values():
            if random() * 100 > pleasure['probability']:
                self.textbox.insert(tk.END, "Удовольствие [{}] запрещено\n".format(pleasure['name']))

    def insert_paragraph(self, schedule_paragraph, start_minute, end_minute):
        """Insert paragraph data to textbox"""
        name = schedule_paragraph['name']
        start_str = minutes_to_time(start_minute)
        if start_minute != end_minute:
            end_str = minutes_to_time(end_minute)
            self.textbox.insert(tk.END, "{} - {} {}\n".format(start_str, end_str, name))
        else:
            self.textbox.insert(tk.END, "{} {}\n".format(start_str, name))

    def insert_work_block(self, schedule_paragraph, start_minute, end_minute):
        """Insert work block data to textbox"""
        minutes_of_work = schedule_paragraph['duration']
        sequence = schedule_paragraph['routines']
        minutes_of_rest = end_minute - start_minute - minutes_of_work
        for routine in sequence:
            minutes_of_work -= routine['duration']
        while minutes_of_work >= 45:
            time_block = choice(range(45, min(120, minutes_of_work) + 1, 15))
            sequence.append({'name': "Цикл работы", 'duration': time_block})
            minutes_of_work -= time_block
        minutes_of_rest += minutes_of_work
        shuffle(sequence)
        sequence.append({'name': "Отдых", 'duration': minutes_of_rest})

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
    # TODO print things to do


class Frame(ABC):

    def __init__(self, main: Main, name: str):
        self.name = name
        self.main = main
        self.frame = tk.LabelFrame(main.main_window, text=name)
        self.pack()

    @abstractmethod
    def pack(self):
        pass

    def clear(self):
        for slave in self.frame.pack_slaves():
            slave.destroy()

    def update(self):
        self.clear()
        self.pack()


class PleasuresFrame(Frame):

    def pack(self):
        pleasures_dictionary = get_pleasures()
        for pleasure in pleasures_dictionary:
            pleasure_object = Pleasure(self.frame, pleasures_dictionary[pleasure])
            pleasure_object.pack()
        add_pleasure = tk.Button(self.frame, text="Добавить удовольствие",
                                 command=lambda: PleasureGetter(self.main).pack())
        self.frame.pack(side=tk.LEFT, anchor=tk.N, fill=tk.Y)
        add_pleasure.pack(side=tk.BOTTOM)


class ScheduleFrame(Frame):
    def pack(self):
        """Create schedule frame"""
        schedule_list = get_schedule() + get_work_blocks()
        schedule_list.sort(key=lambda x: x['start'])
        for paragraph in schedule_list:
            if 'duration' in paragraph.keys():
                WorkBlock(self.frame, paragraph).pack()
            else:
                Paragraph(self.frame, paragraph).pack()
        add_schedule_paragraph = tk.Button(self.frame, text="Добавить пункт плана",
                                           command=lambda: ParagraphGetter(self.main).pack())
        add_work_block = tk.Button(self.frame, text="Добавить блок работы",
                                   command=lambda: WorkBlockGetter(self.main).pack())
        self.frame.pack(side=tk.LEFT, anchor=tk.N, fill=tk.Y)
        add_schedule_paragraph.pack(side=tk.BOTTOM)
        add_work_block.pack(side=tk.BOTTOM)


class RoutinesFrame(Frame):
    def pack(self):
        routines_dict = get_routines()
        for routine in routines_dict.keys():
            Routine(self.frame, routines_dict[routine]).pack()
        add_routine = tk.Button(self.frame, text="Добавить дело",
                                command=lambda: RoutineGetter(self.main).pack())
        self.frame.pack(side=tk.LEFT, anchor=tk.N, fill=tk.Y)
        add_routine.pack(side=tk.BOTTOM)


class Routine:
    """Some thing that sometimes should be done, like sports or cleaning"""

    def __init__(self, master, dictionary):
        self.dictionary = dictionary
        self.frame = tk.Frame(master)
        self.check_buttons = []
        for index in range(len(get_work_blocks())):
            self.check_buttons.append(IndexCheckbutton(index, self))
        self.label = tk.Label(self.frame, text="{name} [{duration}]".format(**dictionary))
        self.delete_button = tk.Button(self.frame, text='X', command=self.destroy)

    def pack(self):
        """Pack routine"""
        self.frame.pack()
        for check_button in self.check_buttons:
            check_button.pack(side=tk.LEFT)
        self.label.pack()
        self.delete_button.pack(side=tk.LEFT)

    def destroy(self):
        """Delete routine"""
        data = get_json_data()
        data['routines'].remove(self.dictionary)
        write_json_data(data)
        self.frame.destroy()


class IndexCheckbutton:
    """Upgraded checkbutton which has its index"""

    def __init__(self, index, master: Routine):
        self.master = master
        self.index = index
        self.variable = tk.BooleanVar(master.frame,
                                      value=index in master.dictionary['active_work_blocks'])
        self.check_button = tk.Checkbutton(master.frame,
                                           variable=self.variable, onvalue=1, offvalue=0,
                                           command=self.change_state)

    def pack(self, side):
        """Pack checkbutton"""
        self.check_button.pack(side=side)

    def change_state(self):
        """Trigger for clicking checkbutton"""
        data = get_json_data()
        name = self.master.dictionary['name']
        if self.variable.get():
            data['routines'][name]['active_work_blocks'].append(self.index)
        else:
            data['routines'][name]['active_work_blocks'].remove(self.index)
        write_json_data(data)


class Pleasure:
    """Pleasure which can be forbidden for the sake of dopamine quality"""

    def __init__(self, master, dictionary):
        self.name = dictionary['name']
        self.probability = tk.IntVar(value=dictionary['probability'])
        self.frame = tk.Frame(master)
        self.label = tk.Label(self.frame, text=self.name)
        self.entry = tk.Entry(self.frame, width=3, textvariable=self.probability)
        self.probability.trace('w', lambda *args: self.__update_json())

    def get_probability(self) -> int:
        """Get probability in entry"""
        try:
            probability = self.probability.get()
        except tk.TclError:
            probability = 0
        return probability

    def increase_probability(self):
        """Increase probability of pleasure allowance"""
        self.probability.set(self.get_probability()+1)
        self.__update_json()

    def decrease_probability(self):
        """Decrease probability of pleasure allowance"""
        self.probability.set(self.get_probability()-1)
        self.__update_json()

    def pack(self):
        """Pack a pleasure"""
        self.frame.pack(anchor=tk.E)
        self.label.pack(side=tk.LEFT)
        self.entry.pack(side=tk.LEFT)
        tk.Button(self.frame, text='+', width=1, height=1,
                  command=self.increase_probability).pack(side=tk.LEFT)
        tk.Button(self.frame, text='-', width=1, height=1,
                  command=self.decrease_probability).pack(side=tk.LEFT)

    def destroy(self):
        self.frame.destroy()

    def dictionary(self):
        """Get data about pleasure as dictionary"""
        return {"name": self.name, "probability": self.get_probability()}

    def __update_json(self):
        """Update pleasure in json"""
        pleasures = get_pleasures()
        pleasures[self.name] = self.dictionary()
        write_pleasures(pleasures)


class Paragraph:
    """Paragraph of schedule"""

    def __init__(self, master, dictionary):
        self.frame = tk.Frame(master)
        self.dictionary = dictionary
        self.text = self.__get_string()
        self.label = tk.Label(self.frame, text=self.text)
        self.delete_button = tk.Button(self.frame, text='X', command=self.destroy)

    def __get_string(self) -> str:
        """Get string with paragraph info"""
        name = self.dictionary['name']
        start_time = self.dictionary['start']
        start_str = minutes_to_time(start_time)
        end_time = self.dictionary['end']
        if start_time != end_time:
            end_str = minutes_to_time(end_time)
            return "{} - {} {}".format(start_str, end_str, name)
        return "{} {}".format(start_str, name)

    def pack(self):
        """Pack paragraph"""
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.RIGHT)

    def destroy(self):
        """Destroy paragraph"""
        data = get_json_data()
        data['schedule'].remove(self.dictionary)
        write_json_data(data)
        self.frame.destroy()


class WorkBlock:
    """
    Work block
    schedule paragraph which will be randomly filled with routines and work times"""

    def __init__(self, master, dictionary):
        self.frame = tk.Frame(master)
        self.dictionary = dictionary
        self.text = self.__get_string()
        self.label = tk.Label(self.frame, text=self.text)
        self.delete_button = tk.Button(self.frame, text='X', command=self.destroy)

    def __get_string(self) -> str:
        """Get a string with work block info"""
        duration = minutes_to_time(self.dictionary['duration'])
        start_time = self.dictionary['start']
        start_str = minutes_to_time(start_time)
        end_time = self.dictionary['end']
        if start_time != end_time:
            end_str = minutes_to_time(end_time)
            return "{} - {} Блок работы [{}]".format(start_str, end_str, duration)
        return "{} Блок работы [{}]".format(start_str, duration)

    def pack(self):
        """Pack work block"""
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.RIGHT)

    def destroy(self):
        """Destroy work block"""
        data = get_json_data()
        data['work_blocks'].remove(self.dictionary)
        write_json_data(data)
        self.frame.destroy()


class NameGetter:
    """Entry for name of something"""

    def __init__(self, window):
        self.name_frame = tk.Frame(window)
        self.name_label = tk.Label(self.name_frame, text="Название")
        self.name_entry = tk.Entry(self.name_frame)

    def pack(self):
        """Pack the frame"""
        self.name_frame.pack()
        self.name_label.pack(side=tk.LEFT)
        self.name_entry.pack(side=tk.LEFT)

    def name(self):
        """Get the name"""
        return self.name_entry.get()


class TimeGetter:
    """Entry for time of something"""

    def __init__(self, window, text):
        self.frame = tk.Frame(window)
        self.label = tk.Label(self.frame, text=text)
        self.hours_entry = ttk.Combobox(self.frame, values=list(range(1, 25)), width=2)
        self.minutes_entry = ttk.Combobox(self.frame, values=list(range(0, 60, 5)), width=2)

    def pack(self):
        """Pack frame"""
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.hours_entry.pack(side=tk.LEFT)
        tk.Label(self.frame, text=':').pack(side=tk.LEFT)
        self.minutes_entry.pack(side=tk.LEFT)

    def time(self):
        """Get time"""
        return int(self.hours_entry.get()) * 60 + int(self.minutes_entry.get())


class NumberGetter:
    """Entry for getting a number"""
    # TODO Replace with TimeGetter when used for gaining time
    def __init__(self, window):
        self.frame = tk.Frame(window)
        self.label = tk.Label(self.frame, text="Длительность")
        self.duration_entry = tk.Entry(self.frame, width=3)

    def pack(self):
        """Pack a frame"""
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.duration_entry.pack(side=tk.LEFT)

    def time(self):
        """Get time"""
        return int(self.duration_entry.get())


class ObjectGetter(ABC):
    """Window with entries for objects like pleasures and work blocks"""

    def __init__(self, master: Main):
        self.master = master
        self.window = tk.Tk()
        self.okay_button = tk.Button(self.window, text="OK",
                                     command=self.append_to_json)

    @abstractmethod
    def pack(self):
        """Create a window with entries"""
        self.okay_button.pack()
        self.window.mainloop()

    @abstractmethod
    def append_to_json(self):
        """Append data about object to json-file"""

    @abstractmethod
    def paragraph(self):
        """Get data about object as dictionary"""


class PleasureGetter(ObjectGetter):
    """Window with entries for pleasure"""

    def __init__(self, master: Main):
        super().__init__(master)
        self.name_frame = NameGetter(self.window)
        self.probability = NumberGetter(self.window)

    def pack(self):
        self.name_frame.pack()
        self.probability.pack()
        super().pack()

    def append_to_json(self):
        """Write data about pleasure to json"""
        paragraph = self.paragraph()
        data = get_json_data()
        data['pleasures'][self.name()] = paragraph
        write_json_data(data)
        self.master.pleasures_frame.update()
        self.window.destroy()

    def paragraph(self) -> dict:
        """Get data about pleasure as dictionary"""
        return {'name': self.name_frame.name(), 'probability': self.probability.time()}

    def name(self):
        """Get pleasure's name"""
        return self.name_frame.name()


class ParagraphGetter(ObjectGetter):
    """Window with entries for schedule paragraph"""

    def __init__(self, master: Main):
        super().__init__(master)
        self.name_frame = NameGetter(self.window)
        self.start_frame = TimeGetter(self.window, "Начало")
        self.end_frame = TimeGetter(self.window, "Конец")

    def pack(self):
        """Create a window and run it"""
        self.name_frame.pack()
        self.start_frame.pack()
        self.end_frame.pack()
        super().pack()

    def append_to_json(self):
        """Write data about schedule paragraph into json"""
        paragraph = self.paragraph()
        data = get_json_data()
        data['schedule'].append(paragraph)
        write_json_data(data)
        self.master.schedule_frame.update()
        self.window.destroy()

    def paragraph(self) -> dict:
        """Get paragraph properties as dictionary"""
        return {"name": self.name_frame.name(),
                "start": self.start_frame.time(),
                "end": self.end_frame.time()}


class RoutineGetter(ObjectGetter):
    """Window with entries for routine"""

    def __init__(self, master: Main):
        super().__init__(master)
        self.name_frame = NameGetter(self.window)
        self.duration_frame = NumberGetter(self.window)

    def pack(self):
        """Create a new window and run it"""
        self.name_frame.pack()
        self.duration_frame.pack()
        super().pack()

    def append_to_json(self):
        """Write data about routine to json"""
        paragraph = self.paragraph()
        data = get_json_data()
        data['routines'][self.name()] = paragraph
        write_json_data(data)
        self.master.routines_frame.update()
        self.window.destroy()

    def paragraph(self) -> dict:
        """Get routine properties as dictionary"""
        return {"name": self.name(),
                "duration": self.duration_frame.time(),
                "active_work_blocks": []}

    def name(self) -> str:
        """Get the name of routine"""
        return self.name_frame.name()


class WorkBlockGetter(ObjectGetter):
    """Window with entries for work block"""

    def __init__(self, master: Main):
        super().__init__(master)
        self.start_frame = TimeGetter(self.window, "Начало")
        self.end_frame = TimeGetter(self.window, "Конец")
        self.duration_frame = NumberGetter(self.window)

    def pack(self):
        """Create a new window and run it"""
        self.start_frame.pack()
        self.end_frame.pack()
        self.duration_frame.pack()
        super().pack()

    def append_to_json(self):
        """Write data about work block into json"""
        paragraph = self.paragraph()
        data = get_json_data()
        data['work_blocks'].append(paragraph)
        data['work_blocks'].sort(key=lambda x: x['start'])
        write_json_data(data)
        self.master.schedule_frame.update()
        self.master.routines_frame.update()
        self.window.destroy()

    def paragraph(self) -> dict:
        """Get work block properties as dictionary"""
        return {"start": self.start_frame.time(),
                "end": self.end_frame.time(),
                "duration": self.duration_frame.time()}


def minutes_to_time(minutes: int) -> str:
    """Converts minutes to format [hh:mm]"""
    return f'{minutes//60:0>2}:{minutes%60:0>2}'


def routines_choose(number):
    """This function is now used now but will be used in future. Don't touch"""
    routines = dict()  # key: name of the routine. value: weigh
    for _ in range(number):
        weigh_sum = sum(routines.values())
        for routine in routines:
            if randint(1, weigh_sum) <= routines[routine]:
                print(routine)
                routines.pop(routine)
                break
            weigh_sum -= routines[routine]


def display_schedule_table(schedule, forbidden_pleasures, day_tuple):
    """This function is now used now but will be used in future. Don't touch"""
    day_today = datetime.datetime(*day_tuple)
    file_name = '../Наработки/Планы.xlsx'
    workbook = load_workbook(file_name)
    worksheet = workbook['Дневной']
    column = get_table_column(worksheet, day_today)
    row = 2
    time = 390
    for routine in schedule:
        cell = worksheet.cell(column=column, row=row)
        routine.table_paragraph(cell, time)
        row += 1
        time += routine.duration

    for pleasure in forbidden_pleasures:
        cell = worksheet.cell(column=column, row=row)
        cell.value = "Нельзя " + pleasure
        row += 1

    workbook.save(file_name)


def get_table_column(worksheet, day_today):
    """This function is now used now but will be used in future. Don't touch"""
    column = 1
    while True:
        cell = worksheet.cell(row=1, column=column)
        if cell.value is None:
            cell.value = day_today
            break
        if cell.value == day_today:
            break
        column += 1
    return column


def get_json_data():
    """Get all the data from json"""
    with open('data.json', 'r', encoding='utf-8') as file:
        return json.load(file)


def get_pleasures() -> dict:
    """Get pleasures"""
    return get_json_data()['pleasures']


def get_schedule() -> list:
    """Get schedule without work blocks"""
    return get_json_data()['schedule']


def get_routines() -> dict:
    """Get routines"""
    return get_json_data()['routines']


def get_work_blocks() -> list:
    """Get work blocks"""
    return get_json_data()['work_blocks']


def write_json_data(data) -> None:
    """Update the json"""
    with open('data.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def write_pleasures(pleasures: dict) -> None:
    """Update pleasures"""
    data = get_json_data()
    data['pleasures'] = pleasures
    write_json_data(data)


if not isfile("data.json"):
    write_json_data({"pleasures": {}, "schedule": [], "work_blocks": [], "routines": {}})

Main()

# TODO Архитектура. Или печатаешь, или возвращаешь
# TODO очистка планов при перезаписи

# TODO GUI
#  TODO Удаление старых удовольствий

# TODO Пофиксить баг, который может случиться, если на одноразовую рутину не хватает времени
