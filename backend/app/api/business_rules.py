from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.database.session import get_db

from app.models.business_entity import (
    BusinessEntity,
)

from app.models.business_rule import (
    BusinessRule,
)

from app.models.metadata import (
    MetadataColumn,
)

from app.schemas.business_rule import (
    BusinessRuleCreate,
    BusinessRuleResponse,
    BusinessRuleUpdate,
)


router = APIRouter(
    prefix="/api/business-rules",
    tags=["Business Rule Registry"],
)


ALLOWED_OPERATORS = {
    "=",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "like",
    "not like",
    "between_or_between",
    "is_null",
    "is_not_null",
}


def business_rule_statement():
    return (
        select(
            BusinessRule
        )
        .options(
            joinedload(
                BusinessRule.entity
            ),
            joinedload(
                BusinessRule.column
            ),
        )
    )


def validate_business_rule(
    database: Session,
    business_entity_id: int,
    metadata_column_id: int,
    operator: str,
):
    entity = database.get(
        BusinessEntity,
        business_entity_id,
    )

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Business entity was not found."
            ),
        )

    if (
        entity.approval_status
        != "approved"
        or not entity.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Business rules can only be created "
                "for approved and active entities."
            ),
        )

    column = database.get(
        MetadataColumn,
        metadata_column_id,
    )

    if column is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Metadata column was not found."
            ),
        )

    if (
        not column.is_discovered
        or not column.is_enabled
        or not column.ai_access_allowed
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The selected metadata column must "
                "be discovered, enabled and approved "
                "for AI access."
            ),
        )

    mapped_table_ids = {
        mapping.metadata_table_id
        for mapping
        in entity.table_mappings
        if mapping.is_active
    }

    if (
        column.metadata_table_id
        not in mapped_table_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The selected metadata column does "
                "not belong to a table mapped to "
                "this business entity."
            ),
        )

    normalized_operator = (
        operator
        .strip()
        .lower()
    )

    if (
        normalized_operator
        not in ALLOWED_OPERATORS
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Unsupported business rule operator."
            ),
        )

    return (
        entity,
        column,
        normalized_operator,
    )


@router.get(
    "",
    response_model=list[
        BusinessRuleResponse
    ],
)
def list_business_rules(
    business_entity_id: int | None = None,
    approval_status: str | None = None,
    is_active: bool | None = None,
    database: Session = Depends(
        get_db
    ),
):
    statement = (
        business_rule_statement()
    )

    if business_entity_id is not None:
        statement = statement.where(
            BusinessRule.business_entity_id
            == business_entity_id
        )

    if approval_status:
        statement = statement.where(
            BusinessRule.approval_status
            == approval_status
        )

    if is_active is not None:
        statement = statement.where(
            BusinessRule.is_active
            .is_(is_active)
        )

    statement = statement.order_by(
        BusinessRule.name
    )

    return list(
        database.scalars(
            statement
        ).unique().all()
    )


@router.get(
    "/{rule_id}",
    response_model=BusinessRuleResponse,
)
def get_business_rule(
    rule_id: int,
    database: Session = Depends(
        get_db
    ),
):
    statement = (
        business_rule_statement()
        .where(
            BusinessRule.id
            == rule_id
        )
    )

    rule = database.scalar(
        statement
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business rule not found",
        )

    return rule


@router.post(
    "",
    response_model=BusinessRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_business_rule(
    payload: BusinessRuleCreate,
    database: Session = Depends(
        get_db
    ),
):
    (
        entity,
        column,
        normalized_operator,
    ) = validate_business_rule(
        database=database,
        business_entity_id=(
            payload.business_entity_id
        ),
        metadata_column_id=(
            payload.metadata_column_id
        ),
        operator=payload.operator,
    )

    rule = BusinessRule(
        business_entity_id=(
            payload.business_entity_id
        ),
        metadata_column_id=(
            payload.metadata_column_id
        ),
        name=payload.name.strip(),
        trigger_phrase=(
            payload.trigger_phrase
            .strip()
            .lower()
        ),
        synonyms=payload.synonyms,
        operator=normalized_operator,
        rule_value=(
            payload.rule_value
            .strip()
        ),
        description=(
            payload.description
        ),
        confidence=(
            payload.confidence
        ),
        approval_status=(
            payload.approval_status
        ),
        is_active=(
            payload.is_active
        ),
    )

    database.add(
        rule
    )

    try:
        database.commit()

        statement = (
            business_rule_statement()
            .where(
                BusinessRule.id
                == rule.id
            )
        )

        return database.scalar(
            statement
        )

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This business rule "
                "already exists."
            ),
        ) from error


@router.put(
    "/{rule_id}",
    response_model=BusinessRuleResponse,
)
def update_business_rule(
    rule_id: int,
    payload: BusinessRuleUpdate,
    database: Session = Depends(
        get_db
    ),
):
    rule = database.get(
        BusinessRule,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business rule not found",
        )

    values = payload.model_dump(
        exclude_unset=True
    )

    new_entity_id = values.get(
        "business_entity_id",
        rule.business_entity_id,
    )

    new_column_id = values.get(
        "metadata_column_id",
        rule.metadata_column_id,
    )

    new_operator = values.get(
        "operator",
        rule.operator,
    )

    (
        entity,
        column,
        normalized_operator,
    ) = validate_business_rule(
        database=database,
        business_entity_id=(
            new_entity_id
        ),
        metadata_column_id=(
            new_column_id
        ),
        operator=new_operator,
    )

    if (
        "trigger_phrase"
        in values
        and values[
            "trigger_phrase"
        ] is not None
    ):
        values[
            "trigger_phrase"
        ] = (
            values[
                "trigger_phrase"
            ]
            .strip()
            .lower()
        )

    if (
        "name"
        in values
        and values["name"] is not None
    ):
        values["name"] = (
            values["name"]
            .strip()
        )

    if (
        "rule_value"
        in values
        and values[
            "rule_value"
        ] is not None
    ):
        values[
            "rule_value"
        ] = (
            values[
                "rule_value"
            ]
            .strip()
        )

    values["operator"] = (
        normalized_operator
    )

    for field_name, value in (
        values.items()
    ):
        setattr(
            rule,
            field_name,
            value,
        )

    try:
        database.commit()

        statement = (
            business_rule_statement()
            .where(
                BusinessRule.id
                == rule_id
            )
        )

        return database.scalar(
            statement
        )

    except IntegrityError as error:
        database.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This business rule "
                "already exists."
            ),
        ) from error


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_business_rule(
    rule_id: int,
    database: Session = Depends(
        get_db
    ),
):
    rule = database.get(
        BusinessRule,
        rule_id,
    )

    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business rule not found",
        )

    database.delete(
        rule
    )

    database.commit()