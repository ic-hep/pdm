"""SQLAlchemy Enum Utility Module."""


def enum_constraint(db, column_name, enum):
    """
    Simulate SQLAlchemy Enum data type.

    Args:
        db (SQLAlchemy): flask_sqlalchemy.SQLAlchemy instance.
        column_name (str): The name of the enum column.
        enum (Enum): The enum.

    Returns:
        tuple: The SQLAlchemy String and CheckConstraint objects
               ready to be used as args to Column.
    """
    names = tuple(value.name for value in enum)
    length = len(max(names, key=len))
    sql = '%s IN %r' % (column_name, names)
    return db.String(length), db.CheckConstraint(sql)
