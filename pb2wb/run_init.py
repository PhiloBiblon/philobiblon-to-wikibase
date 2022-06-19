from init import init
import sys

first_time = False
if len(sys.argv) == 2 and sys.argv[1] == '--firsttime':
  first_time = True

init.init(first_time)
