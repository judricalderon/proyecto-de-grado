items=[];PROPOSALS={"PROP-001"}
def reset():items.clear()
def get(i):return next((x for x in items if x["id"]==i),None)
