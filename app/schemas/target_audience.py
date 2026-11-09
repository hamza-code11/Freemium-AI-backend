from enum import Enum


class TargetAudience(str, Enum):
    KIDS_MEN = "kids_men"
    KIDS_WOMEN = "kids_women"
    TEENAGERS_MEN = "teenagers_men"
    TEENAGERS_WOMEN = "teenagers_women"
    YOUNG_ADULTS_MEN = "young_adults_men"
    YOUNG_ADULTS_WOMEN = "young_adults_women"
    YOUNG_MEN = "young_men"
    YOUNG_WOMEN = "young_women"
    MIDDLE_AGE_MEN = "middle_age_men"
    MIDDLE_AGE_WOMEN = "middle_age_women"
    SENIORS_MEN = "seniors_men"
    SENIORS_WOMEN = "seniors_women"
    