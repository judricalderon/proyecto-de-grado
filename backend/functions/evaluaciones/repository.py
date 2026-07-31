items=[];PROPOSALS={"PROP-001"};PHASES={f"FASE-{i:03}" for i in range(1,8)}
def reset():items.clear()
def get(i):return next((x for x in items if x["id"]==i),None)
