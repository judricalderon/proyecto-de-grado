items=[]
PROPOSALS={"PROP-001"};PHASES={f"FASE-{i:03}" for i in range(1,8)}
def reset():items.clear()
def get(pid,fid):return next((x for x in items if x["id_propuesta"]==pid and x["id_fase"]==fid),None)
