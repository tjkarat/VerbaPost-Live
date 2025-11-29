# --- ADD TO BOTTOM OF database.py ---

def get_civic_leaderboard():
    """
    Analyzes Civic letters to find top states.
    Returns: DataFrame or Dict of top states.
    """
    db = get_session()
    if not db: return []
    try:
        # 1. Fetch only Civic letters (Completed or Pending)
        # We limit to last 500 to keep it fast
        results = db.query(LetterDraft).filter(
            LetterDraft.tier == 'Civic',
            LetterDraft.status.in_(['Completed', 'Pending Admin'])
        ).order_by(LetterDraft.created_at.desc()).limit(500).all()
        
        state_counts = {}
        
        for r in results:
            try:
                # Parse the JSON to find the State
                if r.recipient_json:
                    data = json.loads(r.recipient_json)
                    # Civic letters usually have 'state' in the address object
                    state = data.get('state', '').upper()
                    
                    if state and len(state) == 2: # Filter valid US states
                        state_counts[state] = state_counts.get(state, 0) + 1
            except: 
                continue
                
        # Convert to list sorted by count
        sorted_stats = sorted(state_counts.items(), key=lambda item: item[1], reverse=True)
        return sorted_stats[:5] # Return Top 5
        
    except Exception as e:
        print(f"Leaderboard Error: {e}")
        return []
    finally:
        db.close()