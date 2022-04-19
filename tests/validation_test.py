from pollination.annual_daylight_en17037.entry import AnnualDaylightEN17037EntryPoint
from queenbee.recipe.dag import DAG


def test_annual_daylight_en17037():
    recipe = AnnualDaylightEN17037EntryPoint().queenbee
    assert isinstance(recipe, DAG)
