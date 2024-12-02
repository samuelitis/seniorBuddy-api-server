from .weather import (
    getUltraSrtFcst,
)
from .remind import (
    register_medication_remind,
    register_hospital_remind,
    remove_medication_remind,
    remove_hospital_remind,
    get_medication_remind,
    get_hospital_remind,
    update_meal_time,
)
from .emergency import (
    getHospBasisList,
)
from .device import (
    increase_font_size,
    decrease_font_size,
    send_message,
    call_contact,
    launch_specific_app
)