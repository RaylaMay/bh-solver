import sys
sys.stderr.buffer.write(b'diagnostic flood\n' * 65536)
sys.stderr.buffer.flush()
from bh_sim.worker.entry import main
main()
