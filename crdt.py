# crdt.py

# Inserts a character into the document after the specified after_id.
# Handles conflicts at the same position by sorting lexicographically by ID.
def insert(doc, char_obj, after_id):
    if after_id is None:
        idx = 0
    else:
        idx = -1
        for i, c in enumerate(doc):
            if c['id'] == after_id:
                idx = i + 1
                break
        if idx == -1:
            return  # after_id not found

    # Conflict resolution: skip past elements with a 'greater' ID to maintain 
    # a consistent order across all clients when inserts happen concurrently.
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
