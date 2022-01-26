#
# Simply set execute mode on SIM
#
echo "#!/bin/bash" > SIM
echo "python3 sim.py $@" >> SIM
chmod +x SIM
