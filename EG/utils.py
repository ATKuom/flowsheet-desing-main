import re

class_dict = {
    "Feed": ("F", "S"),
    "Mixer": ("M", "S"),
    "Splitter": ("S", "M"),
    "Heater": ("H", "B"),
    "Cooler": ("C", "B"),
    "HeatExchanger": ("Hx", "S"),
    "Pump": ("Pump", "B"),
    "CSTR": ("Cstr", "B"),
    "PFR": ("Pfr", "B"),
    "Flash": ("Flash", "M"),
    "DistillationColumn": ("Dc", "M"),
    "DistillationColumnwithRecycle": ("Dcr", "M"),
    "Compressor": ("Comp", "B"),
    "Turbine": ("T", "B"),
    "Product": ("P", "S"),
    "Subbranch 1 starter": ("1s", "S"),
    "Subbranch 1 end point": ("1e", "S"),
    "Subbranch 1 connection point": ("1c", "S"),
    "Subbranch 2 starter": ("2s", "S"),
    "Subbranch 2 end point": ("2e", "S"),
    "Subbranch 2 connection point": ("2c", "S"),
    "Subbranch 3 starter": ("3s", "S"),
    "Subbranch 3 end point": ("3e", "S"),
    "Subbranch 3 connection point": ("3c", "S"),
    "HeatExchanger A": ("Hxa", "S"),
    "HeatExchanger B": ("Hxb", "S"),
    "Minorfeed": ("Fm", "S"),
    "Minorproduct": ("Pm", "S"),
    "End": ("End", "S"),
}


equipment_dict = {i: name for i, (name, _) in enumerate(class_dict.items())}
string_integer_dict = {i: code for i, (code, _) in enumerate(class_dict.values())}
equipment_characteristics = {i: char for i, (_, char) in enumerate(class_dict.values())}

Trial_strings = {
    "CstrD": "F1cMHCstrCstrCDcrP1sPump1eEnd",
    "PfrD": "F1cMHPfrCDcrP1sPump1eEnd",
    "Ned1": "FTHxaCCompHxaHPEnd",
    "Ned2": "FTHxaCCompSH1cMHP1sHxa1eEnd",
    "Ned3": "FTHxaCCompHSH1cMHP1sHxa1eEnd",
    "Ned4": "FTHxa2cMHxbCCompSH1cMSHP1sHxa1e2sHxbT2eEnd",
    "Ned5": "FTHxa2cMHxbCCompSH1cMSH3cMHP1sHxb1e2sHxaST2e3s3eEnd",
}


def equipment_to_string(equipment):
    equipment_string = []
    for eq in equipment:
        equipment_string.append(string_integer_dict[eq])
    return "".join(equipment_string)


def string_to_equipment(equipment_string):
    tokens = re.findall(r"[A-Z0-9][a-z]*", equipment_string)
    equipment = []
    for token in tokens:
        for key, value in string_integer_dict.items():
            if value == token:
                equipment.append(key)
                break
    return equipment


def string_to_simplestring(equipment_string):
    """
    Converts a string representation of equipment into a simple string format.
    The simple string format retains only the first letter of each token, with special handling for certain tokens.
    It get rids of end token as well.
    """
    tokens = re.findall(r"[A-Z0-9][a-z]*", equipment_string)
    simplified = ""
    for token in tokens:
        base = token[0]
        rest = token[1:]

        if base in "HCFP":
            if base == "H" and rest.startswith("x"):
                simplified += "Hx"
            else:
                simplified += base + rest
        elif base in "123":
            if rest == "s":
                simplified += "-" + base
            else:
                simplified += base
        else:
            # Drop lowercase letters
            simplified += base

    return simplified[:-1]
