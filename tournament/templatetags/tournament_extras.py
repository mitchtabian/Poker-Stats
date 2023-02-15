from decimal import Decimal
from django import template
from django.template.defaultfilters import stringfilter

from tournament.models import TournamentPlayer
from tournament.util import build_placement_string

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
Format the font-weight.
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

"""
Format placement position.
"""
@register.filter(name='format_placement')
def format_placement(placement):
	return build_placement_string(placement)

"""
Return True if a player has joined the tournament. 
"""
@register.filter(name='has_player_joined_tournament')
@stringfilter
def has_player_joined_tournament(player_id, tournament_id):
	has_joined = TournamentPlayer.objects.has_player_joined_tournament(
		player_id = player_id,
		tournament_id = tournament_id
	)
	return has_joined

"""
Format the "join status" color.
"""
@register.filter(name='format_joined_status_color')
def format_joined_status_color(has_joined):
	if has_joined:
		return "#5cb85c"
	else:
		return "#f0ad4e"

"""
..
"""
@register.filter
def keyvalue(dictionary, key):
	try:
		return dictionary[f'{key}']
	except KeyError:
		return ''

"""
..
"""
@register.filter
def does_value_exist_in_list(data_list, value):
	return value in data_list



















