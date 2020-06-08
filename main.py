from random import randint, choice, shuffle
from openpyxl import load_workbook
import datetime
import json
import tkinter as tk
from os.path import isfile

class Main:

    def __init__(self):
        self.main_window = tk.Tk()
        self.pleasures_frame = self.__create_pleasures_frame()  # TODO Updating probability of pleasure while clicking
        self.schedule_frame = self.__create_schedule_frame()
        self.routines_frame = self.__create_routines_frame()
        self.go_button = tk.Button(self.main_window, text='Вперёд!', command=self.__make_schedule,
                                   height=15, width=20)
        self.go_button.pack(side=tk.BOTTOM, anchor=tk.S)
        self.main_window.mainloop()

    def __create_pleasures_frame(self):
        pleasures_frame = tk.LabelFrame(self.main_window, text="Удовольствия")
        pleasures_dictionary = get_pleasures()
        for pleasure in pleasures_dictionary:
            Pleasure(pleasures_frame, pleasure, pleasures_dictionary[pleasure]).pack()
        add_pleasure = tk.Button(pleasures_frame, text="Добавить удовольствие")
        pleasures_frame.pack(side=tk.LEFT)
        add_pleasure.pack(anchor=tk.S)
        return pleasures_frame

    def __create_schedule_frame(self):
        schedule_frame = tk.LabelFrame(self.main_window, text="Расписание")
        schedule_list = get_schedule() + get_work_blocks()
        schedule_list.sort(key=lambda x: x['start'])
        for paragraph in schedule_list:
            if 'duration' in paragraph.keys():
                WorkBlock(schedule_frame, paragraph).pack()
            else:
                Paragraph(schedule_frame, paragraph).pack()
        add_schedule_paragraph = tk.Button(schedule_frame, text="Добавить пункт плана",
                                           command=lambda: ParagraphGetter(self).pack())
        add_work_block = tk.Button(schedule_frame, text="Добавить блок работы",
                                   command=lambda: WorkBlockGetter(self).pack())
        schedule_frame.pack(side=tk.LEFT, anchor=tk.N)
        add_schedule_paragraph.pack(side=tk.BOTTOM)
        add_work_block.pack(side=tk.BOTTOM)
        return schedule_frame

    def update_schedule_frame(self):
        self.schedule_frame.destroy()
        self.schedule_frame = self.__create_schedule_frame()

    def __create_routines_frame(self):
        routines_frame = tk.LabelFrame(self.main_window, text="Дела")
        routines_dict = get_routines()
        for routine in routines_dict.keys():
            Routine(routines_frame, routines_dict[routine]).pack()
        add_routine = tk.Button(routines_frame, text="Добавить дело", command=lambda: RoutineGetter(self).pack())
        routines_frame.pack(side=tk.LEFT)
        add_routine.pack()
        return routines_frame

    def update_routines_frame(self):
        self.routines_frame.destroy()
        self.routines_frame = self.__create_routines_frame()

    def __make_schedule(self):
        # TODO each press of "GO" button creates new textbox
        textbox = tk.Text(self.main_window)
        textbox.pack()
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
                        textbox.insert(tk.END, "{} {}\n".format(start_str, name))
                    else:
                        start_minute += paragraph['duration']  # we created start_str so we can change start_minute
                        end_str = minutes_to_time(start_minute)
                        textbox.insert(tk.END, "{} - {} {}\n".format(start_str, end_str, name))

            else:  # just a paragraph
                name = schedule_paragraph['name']
                start_str = minutes_to_time(start_minute)
                if start_minute != end_minute:
                    end_str = minutes_to_time(end_minute)
                    textbox.insert(tk.END, "{} - {} {}\n".format(start_str, end_str, name))
                else:
                    textbox.insert(tk.END, "{} {}\n".format(start_str, name))

        print(routines)
        print(work_blocks)
        # TODO напечатать расписание
    # TODO print forbidden pleasures
    # TODO print things to do


class Routine:

    def __init__(self, master, dictionary):
        self.dictionary = dictionary
        self.frame = tk.Frame(master)
        self.check_buttons = []
        for index in range(len(get_work_blocks())):
            self.check_buttons.append(IndexCheckbutton(index, self))
        self.label = tk.Label(self.frame, text="{name} [{duration}]".format(**dictionary))
        self.delete_button = tk.Button(self.frame, text='X', command=self.destroy)

    def pack(self):
        self.frame.pack()
        for check_button in self.check_buttons:
            check_button.pack(side=tk.LEFT)
        self.label.pack()
        self.delete_button.pack(side=tk.LEFT)

    def destroy(self):
        data = get_json_data()
        data['routines'].remove(self.dictionary)
        write_json_data(data)
        self.frame.destroy()


class IndexCheckbutton:

    def __init__(self, index, master: Routine):
        self.master = master
        self.index = index
        self.variable = tk.BooleanVar(master.frame, value=index in master.dictionary['active_work_blocks'])
        self.check_button = tk.Checkbutton(master.frame, variable=self.variable, onvalue=1, offvalue=0,
                                           command=self.change_state)

    def pack(self, side):
        self.check_button.pack(side=side)

    def change_state(self):
        data = get_json_data()
        name = self.master.dictionary['name']
        if self.variable.get():
            data['routines'][name]['active_work_blocks'].append(self.index)
        else:
            data['routines'][name]['active_work_blocks'].remove(self.index)
        write_json_data(data)


class Pleasure:

    def __init__(self, master, text, probability):
        self.frame = tk.Frame(master)
        self.label = tk.Label(self.frame, text=text)
        self.entry = tk.Entry(self.frame, width=3)
        self.entry.insert(tk.END, probability)

    def increase_probability(self):
        probability = int(self.entry.get())
        self.entry.delete(0, tk.END)
        self.entry.insert(tk.END, probability + 1)

    def decrease_probability(self):
        probability = int(self.entry.get())
        self.entry.delete(0, tk.END)
        self.entry.insert(tk.END, probability - 1)

    def pack(self):
        self.frame.pack(anchor=tk.E)
        self.label.pack(side=tk.LEFT)
        self.entry.pack(side=tk.LEFT)
        tk.Button(self.frame, text='+', width=1, height=1, command=self.increase_probability).pack(side=tk.LEFT)
        tk.Button(self.frame, text='-', width=1, height=1, command=self.decrease_probability).pack(side=tk.LEFT)


class Paragraph:

    def __init__(self, master, dictionary):
        self.frame = tk.Frame(master)
        self.dictionary = dictionary
        self.text = self.__get_string()
        self.label = tk.Label(self.frame, text=self.text)
        self.delete_button = tk.Button(self.frame, text='X', command=self.destroy)

    def __get_string(self):
        name = self.dictionary['name']
        start_time = self.dictionary['start']
        start_str = minutes_to_time(start_time)
        end_time = self.dictionary['end']
        if start_time != end_time:
            end_str = minutes_to_time(end_time)
            return "{} - {} {}".format(start_str, end_str, name)
        return "{} {}".format(start_str, name)

    def pack(self):
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.RIGHT)

    def destroy(self):
        data = get_json_data()
        data['schedule'].remove(self.dictionary)
        write_json_data(data)
        self.frame.destroy()


class WorkBlock:

    def __init__(self, master, dictionary):
        self.frame = tk.Frame(master)
        self.dictionary = dictionary
        self.text = self.__get_string()
        self.label = tk.Label(self.frame, text=self.text)
        self.delete_button = tk.Button(self.frame, text='X', command=self.destroy)

    def __get_string(self):
        duration = minutes_to_time(self.dictionary['duration'])
        start_time = self.dictionary['start']
        start_str = minutes_to_time(start_time)
        end_time = self.dictionary['end']
        if start_time != end_time:
            end_str = minutes_to_time(end_time)
            return "{} - {} Блок работы [{}]".format(start_str, end_str, duration)
        return "{} Блок работы [{}]".format(start_str, duration)

    def pack(self):
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.delete_button.pack(side=tk.RIGHT)

    def destroy(self):
        data = get_json_data()
        data['work_blocks'].remove(self.dictionary)
        write_json_data(data)
        self.frame.destroy()


class NameGetter:

    def __init__(self, window):
        self.name_frame = tk.Frame(window)
        self.name_label = tk.Label(self.name_frame, text="Название")
        self.name_entry = tk.Entry(self.name_frame)

    def pack(self):
        self.name_frame.pack()
        self.name_label.pack(side=tk.LEFT)
        self.name_entry.pack(side=tk.LEFT)

    def name(self):
        return self.name_entry.get()


class TimeGetter:

    def __init__(self, window, text):
        self.frame = tk.Frame(window)
        self.label = tk.Label(self.frame, text=text)
        self.hours_entry = tk.Entry(self.frame, width=2)
        self.minutes_entry = tk.Entry(self.frame, width=2)

    def pack(self):
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.hours_entry.pack(side=tk.LEFT)
        tk.Label(self.frame, text=':').pack(side=tk.LEFT)
        self.minutes_entry.pack(side=tk.LEFT)

    def time(self):
        return int(self.hours_entry.get()) * 60 + int(self.minutes_entry.get())


class DurationGetter:

    def __init__(self, window):
        self.frame = tk.Frame(window)
        self.label = tk.Label(self.frame, text="Длительность")
        self.duration_entry = tk.Entry(self.frame, width=3)

    def pack(self):
        self.frame.pack()
        self.label.pack(side=tk.LEFT)
        self.duration_entry.pack(side=tk.LEFT)

    def time(self):
        return int(self.duration_entry.get())


class ParagraphGetter:

    def __init__(self, master: Main):
        self.master = master
        self.window = tk.Tk()
        self.name_frame = NameGetter(self.window)
        self.start_frame = TimeGetter(self.window, "Начало")
        self.end_frame = TimeGetter(self.window, "Конец")
        self.okay_button = tk.Button(self.window, text="OK", command=self.append_schedule_paragraph_to_json)

    def pack(self):
        self.name_frame.pack()
        self.start_frame.pack()
        self.end_frame.pack()
        self.okay_button.pack()
        self.window.mainloop()

    def append_schedule_paragraph_to_json(self):
        paragraph = self.paragraph()
        data = get_json_data()
        data['schedule'].append(paragraph)
        write_json_data(data)
        self.master.update_schedule_frame()
        self.window.destroy()

    def paragraph(self):
        return {"name": self.name_frame.name(),
                "start": self.start_frame.time(),
                "end": self.end_frame.time()}


class RoutineGetter:

    def __init__(self, master: Main):
        self.master = master
        self.window = tk.Tk()
        self.name_frame = NameGetter(self.window)
        self.duration_frame = DurationGetter(self.window)
        self.okay_button = tk.Button(self.window, text="OK", command=self.append_routine_to_json)

    def pack(self):
        self.name_frame.pack()
        self.duration_frame.pack()
        self.okay_button.pack()
        self.window.mainloop()

    def append_routine_to_json(self):
        paragraph = self.paragraph()
        data = get_json_data()
        data['routines'][self.name()] = paragraph
        write_json_data(data)
        self.master.update_routines_frame()
        self.window.destroy()

    def paragraph(self):
        return {"name": self.name(),
                "duration": self.duration_frame.time(),
                "active_work_blocks": []}

    def name(self):
        return self.name_frame.name()


class WorkBlockGetter:

    def __init__(self, master: Main):
        self.master = master
        self.window = tk.Tk()
        self.start_frame = TimeGetter(self.window, "Начало")
        self.end_frame = TimeGetter(self.window, "Конец")
        self.duration_frame = DurationGetter(self.window)
        self.okay_button = tk.Button(self.window, text="OK", command=self.append_work_block_to_json)

    def pack(self):
        self.start_frame.pack()
        self.end_frame.pack()
        self.duration_frame.pack()
        self.okay_button.pack()
        self.window.mainloop()

    def append_work_block_to_json(self):
        paragraph = self.paragraph()
        data = get_json_data()
        data['work_blocks'].append(paragraph)
        data['work_blocks'].sort(key=lambda x: x['start'])
        write_json_data(data)
        self.master.update_schedule_frame()
        self.master.update_routines_frame()
        self.window.destroy()

    def paragraph(self):
        return {"start": self.start_frame.time(),
                "end": self.end_frame.time(),
                "duration": self.duration_frame.time()}


def minutes_to_time(minutes: int):
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
    wb = load_workbook(file_name)
    ws = wb['Дневной']
    column = get_table_column(ws, day_today)
    row = 2
    time = 390
    for routine in schedule:
        cell = ws.cell(column=column, row=row)
        routine.table_paragraph(cell, time)
        row += 1
        time += routine.duration

    for pleasure in forbidden_pleasures:
        cell = ws.cell(column=column, row=row)
        cell.value = "Нельзя " + pleasure
        row += 1

    wb.save(file_name)


def get_table_column(worksheet, day_today):
    """This function is now used now but will be used in future. Don't touch"""
    column = 1
    while True:
        cell = worksheet.cell(row=1, column=column)
        if cell.value is None:
            cell.value = day_today
            break
        elif cell.value == day_today:
            break
        column += 1
    return column


def get_json_data():
    with open('data.json', 'r', encoding='utf-8') as file:
        return json.load(file)


def get_pleasures():
    return get_json_data()['pleasures']


def get_schedule():
    return get_json_data()['schedule']


def get_routines() -> dict:
    return get_json_data()['routines']


def get_work_blocks() -> list:
    return get_json_data()['work_blocks']


def write_json_data(data):
    with open('data.json', 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

if not isfile("data.json"):
    with open("data.json", "w") as file:
        json.dump({
            "pleasures": [],
            "schedule": [],
            "work_blocks": [],
            "routines": {}
            }, file, indent=4)        
Main()

# TODO Архитектура. Или печатаешь, или возвращаешь
# TODO очистка планов при перезаписи

# TODO GUI
#  TODO Кнопка редактирования удовольствия
#  TODO Запись новых удовольствий
#  TODO Удаление старых удовольствий

# TODO Пофиксить баг, который может случиться, если на одноразовую рутину не хватает времени

# TODO Вместо удаления и повторного создания рамки, перезаполнять её
