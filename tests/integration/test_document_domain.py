from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

from doclens_ai.models import Document, DocumentVersion, Workspace


def _version(document: Document, number: int = 1) -> DocumentVersion:
    return DocumentVersion(
        document=document,
        version_number=number,
        original_filename="example.pdf",
        content_type="application/pdf",
        file_size=1024,
        sha256_checksum="a" * 64,
        object_storage_key=f"documents/{document.id}/versions/{number}/source.pdf",
    )


@pytest.mark.integration
def test_document_domain_relationships_and_workspace_scope(migrated_database_url: str) -> None:
    async def exercise_domain() -> None:
        engine = create_async_engine(migrated_database_url)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as session:
                first_workspace = Workspace(name="First workspace")
                second_workspace = Workspace(name="Second workspace")
                first_document = Document(workspace=first_workspace)
                second_document = Document(workspace=second_workspace)
                first_version = _version(first_document)
                repeated_content_version = _version(first_document, number=2)
                second_version = _version(second_document)
                session.add_all([first_version, repeated_content_version, second_version])
                await session.commit()

                query = (
                    select(Document)
                    .where(Document.workspace_id == first_workspace.id)
                    .options(selectinload(Document.workspace), selectinload(Document.versions))
                )
                scoped_documents = (await session.scalars(query)).all()

                assert [document.id for document in scoped_documents] == [first_document.id]
                assert scoped_documents[0].workspace.id == first_workspace.id
                assert [version.id for version in scoped_documents[0].versions] == [
                    first_version.id,
                    repeated_content_version.id,
                ]
                assert first_version.sha256_checksum == repeated_content_version.sha256_checksum
                assert second_document.workspace_id == second_workspace.id
                assert first_workspace.id != second_workspace.id
        finally:
            await engine.dispose()

    asyncio.run(exercise_domain())


@pytest.mark.integration
def test_duplicate_version_number_is_rejected(migrated_database_url: str) -> None:
    async def create_duplicates() -> None:
        engine = create_async_engine(migrated_database_url)
        try:
            async with AsyncSession(engine) as session:
                document = Document(workspace=Workspace(name="Workspace"))
                session.add_all([_version(document), _version(document)])
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await engine.dispose()

    asyncio.run(create_duplicates())


@pytest.mark.integration
def test_invalid_foreign_keys_are_rejected(migrated_database_url: str) -> None:
    async def create_orphans() -> None:
        engine = create_async_engine(migrated_database_url)
        try:
            async with AsyncSession(engine) as session:
                session.add(Document(workspace_id=uuid4()))
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()

                session.add(
                    DocumentVersion(
                        document_id=uuid4(),
                        version_number=1,
                        original_filename="orphan.pdf",
                        content_type="application/pdf",
                        file_size=1,
                        sha256_checksum="b" * 64,
                        object_storage_key="orphan/source.pdf",
                    )
                )
                with pytest.raises(IntegrityError):
                    await session.commit()
                await session.rollback()
        finally:
            await engine.dispose()

    asyncio.run(create_orphans())
