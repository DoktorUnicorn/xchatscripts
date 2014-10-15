import xchat, datetime, pytz, math

'''
To all the followers of the most divine NemusBot, take heed:

No longer must we live in fear of accidentally profaning the holy ALL CAPS FRIDAY
Just install this script and it will:
	* UPPERCASE everything during ALL CAPS FRIDAY on #dc801
	* Change your nick to be UPPERCASE at the start of ALL CAPS FRIDAY
	* Change your nick back to its original at the end
		* (This part may be a bit buggy)
	* Point out when someone dares to speak in lowercase on ALL CAPS FRIDAY
		* Does this by a non-obtrusive, non-spammy inline message that only you see
'''

__module_name__ = "t"
__module_version__ = "0.1"
__module_description__ = "ALL CAPS FRIDAY automated (#dc801 on FreeNode)"

# ALL CAPS FRIDAY begins
# UTC: Friday @ 19:00:00
# UTC: Friday @ 18:00:00 during mountain DST
# ALL CAPS FRIDAY ends
# UTC: Saturday @ 07:00:00
# UTC: Saturday @ 06:00:00 during mountain DST

global original_nick, timer_begins, timer_ends, command_lock
global uppercase_hook, action_hook, nick_hook, heretic_hook
global utc, mtn, ACF_BEGIN_TIME, ACF_END_TIME
global CHANNEL_NAME, NETWORK_NAME, has_joined
utc = pytz.utc
mtn = pytz.timezone('US/Mountain')
ACF_BEGIN_TIME = (1, 19)
ACF_END_TIME = (2, 7)
#CHANNEL_NAME = "#dc801"
CHANNEL_NAME = "#nulinx"
NETWORK_NAME = "FreeNode"
has_joined = False
command_lock = False

def dc801_channel():
	print "dc801_channel"
	''' Is this channel #dc801 on FreeNode? '''
	global CHANNEL_NAME, NETWORK_NAME
	net = xchat.get_info("network")
	chan = xchat.get_info("channel")
	return net==NETWORK_NAME and chan==CHANNEL_NAME

def all_caps_friday():
	print "all_caps_friday"
	''' Fridays from noon until midnight US mountain time '''
	global utc, mtn
	now_utc = datetime.datetime.utcnow().replace(tzinfo=utc)
	now_mtn = now_utc.astimezone(mtn)
	return now_mtn.weekday() == 1 and now_mtn.hour >= 12

def time_to(event, timezone=mtn):
	print "time_to"
	'''
	Returns milliseconds until next wkday at hour.
	0=Monday, 6=Sunday. Hour is 24-hr time.
	Specify wkday and hour in UTC. Timezone is only used to guess
	at daylight savings time, and doesn't work for all times.

	This could really use a better implementation. I also hate DST,
	leapseconds, leapdays, and the whole notion of basing time around
	horribly inaccurate clocks such as the earth's spin and rotation around
	the Sun. Everyone should just use atomic time, or at least UTC.
	'''
	global utc, mtn
	wkday = event[0]
	hour = event[1]
	now = datetime.datetime.utcnow().replace(tzinfo=utc)
	day_dif = wkday - now.weekday()
	if day_dif < 0:
		day_dif += 7
	target = now + datetime.timedelta(days=day_dif)
	end = datetime.datetime(target.year, target.month, target.day, hour, tzinfo=utc)
	if end.astimezone(timezone).timetuple().tm_isdst > 0:
		end = end + datetime.timedelta(hours=-1)
	if now > end:
		end = end + datetime.timedelta(days=7)
	to_end = int(math.ceil((end - now).total_seconds()*1000))
	return to_end

def to_uppercase(word, word_eol, userdata):
	print "to_uppercase"
	''' UPPERCASES everything you write to #dc801 during ACF '''
	if dc801_channel() and all_caps_friday():
		s=word_eol[0].upper()
		cmd = "privmsg %s :%s" % (xchat.get_info('channel'), s)
		xchat.command(cmd)
		return xchat.EAT_ALL
	else:
		return xchat.EAT_NONE

def to_uppercase_action(word, word_eol, userdata):
	print "to_uppercase_action"
	''' UPPERCASES /me's you write to #dc801 during ACF '''
	global command_lock
	if dc801_channel() and all_caps_friday():
		if not command_lock:
			s=word_eol[1].upper()
			cmd = "me %s" % s
			command_lock = True
			xchat.command(cmd)
			return xchat.EAT_ALL
		else:
			command_lock = False
	return xchat.EAT_NONE

def change_nick(word, word_eol, userdata):
	print "change_nick"
	'''
	UPPERCASES your FreeNode nick if you /nick during ACF and are in #dc801.
	Also keeps track of what you typed in as your nickname so it can be restored
	to it's original case-sensitive form when ACF ends or you leave #dc801
	'''
	global original_nick
	global NETWORK_NAME, CHANNEL_NAME
	dc801 = xchat.find_context(NETWORK_NAME, CHANNEL_NAME)
	if dc801:
		requested_nick = word[1]
		original_nick = requested_nick
		if all_caps_friday() and requested_nick.islower():
			new_nick = requested_nick.upper()
			cmd = "nick %s" % new_nick
			dc801.command(cmd)
			return xchat.EAT_ALL
		else:
			new_nick = requested_nick
	return xchat.EAT_NONE

def join_dc801(word, word_eol, userdata):
	print "join_dc801"
	'''
	UPPERCASES your nickname upon joining #dc801 during ACF. Also keeps track
	of your original nickname so it can be restored when ACF ends or you leave
	#dc801. Also sets the ACF end and ACF start timers.
	'''
	global NETWORK_NAME, CHANNEL_NAME, has_joined
	channel = word[1]
	net = xchat.get_info("network")
	code = xchat.EAT_NONE
	if channel == CHANNEL_NAME and net == NETWORK_NAME and not has_joined:
		code = initialize()
	return code

def initialize():
	print "initialize"
	global original_nick, timer_begins, timer_ends
	global uppercase_hook, action_hook, nick_hook, heretic_hook
	global ACF_BEGIN_TIME, ACF_END_TIME, has_joined
	has_joined = True
	hooks = [timer_begins, timer_ends, uppercase_hook, action_hook, nick_hook, heretic_hook]
	for h in hooks:
		if h is not None:
			xchat.unhook(h)
			h = None
	timer_begins = xchat.hook_timer(time_to(ACF_BEGIN_TIME), ACF_begin)
	timer_ends = xchat.hook_timer(time_to(ACF_END_TIME), ACF_end)
	uppercase_hook = xchat.hook_command("", to_uppercase)
	action_hook = xchat.hook_command("me", to_uppercase_action)
	nick_hook = xchat.hook_command("nick", change_nick)
	heretic_hook = xchat.hook_server("PRIVMSG", heretic_patrol)
	xchat.hook_command("leave", leave_dc801)
	original_nick = xchat.get_info("nick")
	if all_caps_friday() and original_nick.islower():
		new_nick = original_nick.upper()
		cmd = "nick %s" % new_nick
		xchat.command(cmd)
		return xchat.EAT_ALL
	return xchat.EAT_NONE

def leave_dc801(word, word_eol, userdata):
	print "leave_dc801"
	'''
	Restores your current nickname back to the case-sensitive form you last
	entered it in as. Also stops the ALL CAPS FRIDAY timers.
	'''
	global original_nick, timer_begins, timer_ends
	global uppercase_hook, action_hook, nick_hook, heretic_hook
	global NETWORK_NAME, CHANNEL_NAME, has_joined
	has_joined = False
	channel = word[1]
	net = xchat.get_info("network")
	if channel == CHANNEL_NAME and net == NETWORK_NAME:
		hooks = [timer_begins, timer_ends, uppercase_hook, action_hook, nick_hook, heretic_hook]
		for h in hooks:
			if h is not None:
				xchat.unhook(h)
				h = None
		current_nick = xchat.get_info("nick")
		if original_nick != current_nick:
			cmd = "nick %s" % original_nick
			xchat.command(cmd)
			return xchat.EAT_ALL
	return xchat.EAT_NONE

def ACF_begin(word, word_eol, userdata):
	print "ACF_begin"
	global original_nick, timer_begins, ACF_BEGIN_TIME
	global NETWORK_NAME, CHANNEL_NAME
	dc801 = xchat.find_context(NETWORK_NAME, CHANNEL_NAME)
	if dc801:
		timer_begins = xchat.hook_timer(time_to(ACF_BEGIN_TIME), AFC_begin)
		current_nick = dc801.get_info("nick")
		if current_nick != original_nick:
			msg = "Inconsistent nickname state. Ori: %s Cur: %s" % (
			      original_nick, current_nick)
			raise Exception(msg)
		if current_nick.islower():
			new_nick = current_nick.upper()
			cmd = "nick %s" % new_nick
			dc801.command(cmd)
	return 0

def ACF_end(word, word_eol, userdata):
	print "ACF_end"
	global original_nick, timer_ends, ACF_END_TIME
	global NETWORK_NAME, CHANNEL_NAME
	dc801 = xchat.find_context(NETWORK_NAME, CHANNEL_NAME)
	if dc801:
		timer_ends = xchat.hook_timer(time_to(ACF_END_TIME), AFC_end)
		current_nick = dc801.get_info("nick")
		if current_nick.islower():
			msg = "Inconsistent nickname state. Ori: %s Cur: %s" % (
			      original_nick, current_nick)
			raise Exception(msg)
		if original_nick.islower():
			cmd = "nick %s" % original_nick
			dc801.command(cmd)
			return 0
		elif original_nick != current_nick:
			msg = "Inconsistent nickname state. Ori: %s Cur %s" % (
			      original_nick, current_nick)
			raise Exception(msg)
	return 0

def heretic_patrol(word, word_eol, userdata):
	print "heretic_patrol"
	''' Highlights taboo lower case messages in blue during ACF on #dc801 '''
	if dc801_channel() and word[2] == CHANNEL_NAME and all_caps_friday():
		if not word_eol[3].isupper():
			heretic = word[0][1:word[0].find("!")]
			print "%s PROFANED ALL CAPS FRIDAY" % heretic
	return xchat.EAT_NONE

print "t.py has been loaded"
timer_begins = None
timer_ends = None
uppercase_hook = None
action_hook = None
nick_hook = None
heretic_hook = None
if xchat.find_context(NETWORK_NAME, CHANNEL_NAME):
	initialize()
xchat.hook_command("join", join_dc801)
