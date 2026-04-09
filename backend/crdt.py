# crdt.py
# Core Conflict-free Replicated Data Type engine for concurrent editing.
# Ensures that characters inserted concurrently always arrive at the same final state.

# Inserts a character into the document after the specified after_id.
# Handles conflicts by sorting lexicographically by ID if inserted concurrently.
def insert(doc, char_obj, after_id):
    idx = 0 if after_id is None else -1
    if after_id is not None:
        for i, c in enumerate(doc):
            if c['id'] == after_id:
                idx = i + 1
                break
        if idx == -1: return

    # Conflict resolution: skip elements with greater IDs.
    while idx < len(doc) and doc[idx]['id'] > char_obj['id']:
        idx += 1
        
    doc.insert(idx, char_obj)

# Marks a character as deleted (tombstone deletion) without removing it.
def delete(doc, char_id):
    for c in doc:
        if c['id'] == char_id:
            c['deleted'] = True
            break

# Constructs and returns the final string, ignoring any deleted characters.
def to_string(doc):
    return "".join(c['char'] for c in doc if not c['deleted'])
