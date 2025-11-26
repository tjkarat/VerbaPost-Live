def update_status(order_id, new_status):
    db = get_session()
    if not db: return
    try:
        draft = db.query(LetterDraft).filter(LetterDraft.id == order_id).first()
        if draft:
            draft.status = new_status
            db.commit()
    except: pass
    finally: db.close()