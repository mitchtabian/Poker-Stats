from decimal import Decimal
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

"""
Used to format the way money is displayed.
Ex: 0.00 -> --
Ex: 5.56 -> $5.67
"""
@register.filter(name='format_money')
@stringfilter
def format_money(money_string):
	if money_string == "0.00":
		return "--"
	else:
		money_value = Decimal(money_string)
		if money_value < 0:
			return f"-${abs(money_value)}"
		return f"${money_string}"

"""
Used to format a number such that '0' becomes '--'.
Ex: 0 -> --
Ex: 5 -> 5
"""
@register.filter(name='format_table_number')
@stringfilter
def format_table_number(num_eliminations):
	if num_eliminations == "0":
		return "--"
	else:
		return f"{num_eliminations}"

"""
Used to format the placement color for a Player in the Tournemnt.
Ex: If payout_percentages = (50, 30, 20) then 1st, 2nd and 3rd will be "#5cb85c" (green)
"""
@register.filter(name='placement_color')
@stringfilter
def placement_color(placement, placements):
	split_placements = placements.split(",")
	if placement in split_placements:
		return "#5cb85c"
	else:
		return "#d9534f"

"""
Format the color of an earnings row.
Green for positive.
Red for negative.
Black for 0.
"""
@register.filter(name='format_table_number_color')
@stringfilter
def format_table_number_color(number):
	decimal_number = Decimal(number)
	zero = Decimal(0.00)
	if decimal_number > zero:
		return "#5cb85c"
	elif decimal_number < zero:
		return "#d9534f"
	else:
		return "#292b2c"

"""
..
"""
@register.filter(name='format_number_weight')
@stringfilter
def format_number_weight(number):
	decimal_number = Decimal(number)
	zero = Decimal(0.00)
	if decimal_number != zero:
		return 550
	else: 
		return 400













