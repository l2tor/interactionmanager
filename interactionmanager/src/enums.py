from enum import Enum
import json

Move_State = Enum('Move_State', 'Static f_Static Movable')

PUBLIC_ENUMS_VALUES = {
    'Static': type(Move_State.Static),
    'f_Static': type(Move_State.f_Static),
    'Movable': type(Move_State.Movable)
}

PUBLIC_ENUMS = {
    "Move_State": Move_State
}


class EnumEncoder(json.JSONEncoder):
    def default(self, obj):
        if type(obj) in PUBLIC_ENUMS.values():
            return {"__enum__": str(obj)}
        return json.JSONEncoder.default(self, obj)


def as_enum(d):
    if "__enum__" in d:
        name, member = d["__enum__"].split(".")
        return getattr(PUBLIC_ENUMS[name], member)
    else:
        return d
