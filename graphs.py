import uuid
from supabaseClient import supabase

def add_graph(graph: dict, phone_number: str) -> dict:
    """
    Inserts a graph config into 'graphs' for the user with this phone_number,
    then seeds initial data in 'graph_data'.
    Returns the inserted graph row.
    """
    # 1) lookup user_data.id by phone_number
    try:
        ud_resp = (
            supabase
            .table("user_data")
            .select("id")
            .eq("phone_number", phone_number)
            .single()
            .execute()
        )
    except Exception as e:
        raise RuntimeError(f"Failed to fetch user_data for {phone_number}: {e}")

    if not ud_resp.data or "id" not in ud_resp.data:
        raise RuntimeError(f"No user_data row found with phone_number={phone_number}")

    user_data_id = ud_resp.data["id"]

    # 2) generate a UUID for this graph
    graph_id = str(uuid.uuid4())

    # 3) build the record for insertion (including the FK)
    graph_record = {
        "id":             graph_id,
        "user_data_id":   user_data_id,
        "title":          graph["title"],
        "description":    graph["description"],
        "type":           graph["type"],
        "settings":       graph["settings"],
    }

    # 4) insert into 'graphs'
    try:
        resp = supabase.table("graphs").insert([graph_record]).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase insert (graphs) failed: {e}")

    updated_rows = getattr(resp, "data", None)
    if not updated_rows or not isinstance(updated_rows, list):
        raise RuntimeError("Error adding the graph!")

    # 5) seed an empty data array into 'graph_data'
    try:
        data_resp = supabase.table("graph_data").insert([{
            "graph_id": graph_id,
            "data":     []
        }]).execute()
    except Exception as e:
        raise RuntimeError(f"Supabase insert (graph_data) failed: {e}")

    return graph_id
