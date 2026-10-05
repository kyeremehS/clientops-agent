# 0004 — Pin SQLAlchemy to the 2.0 line

Status: accepted

Two environment findings drove this:

1. SQLAlchemy 2.1 imports its C extensions unconditionally, and the 2.1.3
   `_collections_cy` DLL is blocked by Application Control policy on the
   Windows dev machine (`import sqlalchemy` fails).
2. SQLAlchemy 2.0.36 (pure-Python wheel) imports but mishandles `X | None`
   annotations on Python 3.14 (`make_union_type` TypeError).

SQLAlchemy 2.0.54 imports cleanly on the dev machine and handles 3.14 typing.
The 2.0 ORM API (`mapped_column`, `Mapped`, `Uuid`) covers everything B1–B6 needs.

Decision: pin `sqlalchemy>=2.0,<2.1`. Revisit if we need a 2.1-only feature.
