from __future__ import annotations

from dataclasses import dataclass, field

from app.database.session import SessionLocal
from app.ai.sql_compiler import (
    create_and_compile_sql,
)


@dataclass
class PromptExpectation:
    decision: str = "approved"

    must_contain_sql: list[str] = field(
        default_factory=list
    )

    must_not_contain_sql: list[str] = field(
        default_factory=list
    )

    expected_entities: list[str] = field(
        default_factory=list
    )

    expected_tables: list[str] = field(
        default_factory=list
    )

    expected_filter_columns: list[str] = field(
        default_factory=list
    )

    expected_group_by_columns: list[str] = field(
        default_factory=list
    )

    expected_join_ready: bool | None = None

    expect_aggregation: bool | None = None


@dataclass
class PromptTest:
    name: str
    prompt: str
    expected: PromptExpectation


TESTS = [
    PromptTest(
        name="Active Vehicles",
        prompt="Show active vehicles",
        expected=PromptExpectation(
            expected_entities=[
                "Vehicles",
            ],
            expected_tables=[
                "fleet_vehicles",
            ],
            expected_filter_columns=[
                "status",
            ],
            must_contain_sql=[
                "`status` =",
                "fleet_vehicles",
            ],
            must_not_contain_sql=[
                "`vehicle_no` =",
            ],
        ),
    ),

    PromptTest(
        name="Pending Trip Drivers",
        prompt=(
            "Show drivers associated "
            "with pending trips"
        ),
        expected=PromptExpectation(
            expected_entities=[
                "Drivers",
                "Trip",
            ],
            expected_tables=[
                "fleet_drivers",
                "fleet_trip",
            ],
            expected_filter_columns=[
                "status",
            ],
            expected_join_ready=True,
            must_contain_sql=[
                "INNER JOIN",
                "`driver_name`",
                "`status` =",
            ],
        ),
    ),

    PromptTest(
        name="Vehicles Under Maintenance",
        prompt=(
            "Show vehicles under maintenance"
        ),
        expected=PromptExpectation(
            expected_entities=[
                "Vehicles",
                "Maintenance",
            ],
            expected_filter_columns=[
                "status",
            ],
            expected_join_ready=True,
            must_contain_sql=[
                "INNER JOIN",
                "`status` =",
            ],
        ),
    ),

    PromptTest(
        name="Trips By Department",
        prompt=(
            "Show trips by department "
            "this month"
        ),
        expected=PromptExpectation(
            expected_entities=[
                "Trip",
            ],
            expected_tables=[
                "fleet_trip",
            ],
            expected_filter_columns=[
                "start_date",
            ],
            expect_aggregation=False,
            must_contain_sql=[
                "`start_date` >=",
                "`start_date` <",
            ],
            must_not_contain_sql=[
                "GROUP BY",
                "`date_completed` >=",
            ],
        ),
    ),

    PromptTest(
        name="Count Active Drivers",
        prompt="Count active drivers",
        expected=PromptExpectation(
            expected_entities=[
                "Drivers",
            ],
            expected_tables=[
                "fleet_drivers",
            ],
            expected_filter_columns=[
                "status",
            ],
            expect_aggregation=True,
            must_contain_sql=[
                "COUNT(*)",
                "`status` =",
            ],
        ),
    ),

    PromptTest(
        name="Top Vehicles By Fuel Cost",
        prompt=(
            "Show top 10 vehicles "
            "by fuel cost"
        ),
        expected=PromptExpectation(
            decision="approved",
            must_not_contain_sql=[
                "COUNT(*)",
                "SUM(`t1`.`id`)",
            ],
        ),
    ),

    PromptTest(
        name="Total Trips By Department",
        prompt=(
            "Show total trips "
            "by department"
        ),
        expected=PromptExpectation(
            expected_entities=[
                "Trip",
            ],
            expected_tables=[
                "fleet_trip",
            ],
            expected_group_by_columns=[
                "department",
            ],
            expect_aggregation=True,
            must_contain_sql=[
                "COUNT(*)",
                "GROUP BY",
                "`department`",
            ],
        ),
    ),

    PromptTest(
        name="Expiring Driver Licenses",
        prompt=(
            "Show drivers whose license "
            "expires this month"
        ),
        expected=PromptExpectation(
            expected_entities=[
                "Drivers",
            ],
            expected_tables=[
                "fleet_drivers",
            ],
            expected_filter_columns=[
                "license_expiry_date",
            ],
            must_contain_sql=[
                "`license_expiry_date` >=",
                "`license_expiry_date` <",
            ],
        ),
    ),

    PromptTest(
        name="Emergency Trips",
        prompt="Show emergency trips",
        expected=PromptExpectation(
            expected_entities=[
                "Trip",
            ],
            expected_tables=[
                "fleet_trip",
            ],
            expected_filter_columns=[
                "emergency",
            ],
            must_contain_sql=[
                "`emergency` =",
            ],
        ),
    ),

    PromptTest(
        name="Completed Trips",
        prompt=(
            "Show completed trips "
            "this month"
        ),
        expected=PromptExpectation(
            expected_entities=[
                "Trip",
            ],
            expected_tables=[
                "fleet_trip",
            ],
            expected_filter_columns=[
                "date_completed",
                "status",
            ],
            must_contain_sql=[
                "`date_completed` >=",
                "`date_completed` <",
                "`status` =",
            ],
            must_not_contain_sql=[
                "`start_date` >=",
            ],
        ),
    ),

    PromptTest(
        name="Assigned Vehicles",
        prompt=(
            "Show vehicles assigned "
            "to drivers"
        ),
        expected=PromptExpectation(
            expected_entities=[
                "Vehicles",
                "Drivers",
            ],
            expected_filter_columns=[
                "assigned",
            ],
            expected_join_ready=True,
            must_contain_sql=[
                "INNER JOIN",
                "`plate_no`",
                "`assigned` =",
            ],
        ),
    ),

    PromptTest(
        name="Expired Driver Licenses",
        prompt=(
            "Show drivers with "
            "expired licenses"
        ),
        expected=PromptExpectation(
            expected_entities=[
                "Drivers",
            ],
            expected_tables=[
                "fleet_drivers",
            ],
            expected_filter_columns=[
                "license_expiry_date",
            ],
            must_contain_sql=[
                "`license_expiry_date` <",
            ],
            must_not_contain_sql=[
                "`driver_no` =",
            ],
        ),
    ),
]


def value(
    obj,
    name,
    default=None,
):
    if isinstance(
        obj,
        dict,
    ):
        return obj.get(
            name,
            default,
        )

    return getattr(
        obj,
        name,
        default,
    )


def names(
    items,
    attribute,
):
    result = []

    for item in items or []:
        target = value(
            item,
            attribute,
        )

        if target is None:
            continue

        name = value(
            target,
            "name",
        )

        if name:
            result.append(
                name
            )

    return result


def normalize_sql(
    sql: str | None,
) -> str:
    if not sql:
        return ""

    return " ".join(
        sql.split()
    )


def extract_entity_names(
    plan,
) -> list[str]:
    if plan is None:
        return []

    reasoning = value(
        plan,
        "reasoning_result",
        {},
    )

    entity_matches = value(
        reasoning,
        "matched_entities",
        [],
    )

    return names(
        entity_matches,
        "entity",
    )


def extract_table_names(
    plan,
) -> list[str]:
    if plan is None:
        return []

    reasoning = value(
        plan,
        "reasoning_result",
        {},
    )

    physical_tables = value(
        reasoning,
        "physical_tables",
        [],
    )

    table_names = []

    for item in physical_tables:
        table = value(
            item,
            "table",
        )

        table_name = value(
            table,
            "table_name",
        )

        if table_name:
            table_names.append(
                table_name
            )

    return list(
        dict.fromkeys(
            table_names
        )
    )


def extract_filter_columns(
    plan,
) -> list[str]:
    if plan is None:
        return []

    filters = value(
        plan,
        "filters",
        [],
    ) or []

    result = []

    for item in filters:
        resolved_column = value(
            item,
            "resolved_column",
        )

        column = value(
            resolved_column,
            "column",
        )

        column_name = value(
            column,
            "column_name",
        )

        if column_name:
            result.append(
                column_name
            )

    return result


def extract_group_by_columns(
    plan,
) -> list[str]:
    if plan is None:
        return []

    groups = value(
        plan,
        "group_by",
        [],
    ) or []

    result = []

    for item in groups:
        resolved_column = value(
            item,
            "resolved_column",
        )

        column = value(
            resolved_column,
            "column",
        )

        column_name = value(
            column,
            "column_name",
        )

        if column_name:
            result.append(
                column_name
            )

    return result


def semantic_join_ready(
    plan,
) -> bool:
    if plan is None:
        return False

    joins = value(
        plan,
        "semantic_joins",
        [],
    ) or []

    if not joins:
        return False

    return all(
        bool(
            value(
                join,
                "physical_join_ready",
                False,
            )
        )
        for join in joins
    )


def aggregation_present(
    plan,
) -> bool:
    if plan is None:
        return False

    return (
        value(
            plan,
            "aggregation",
        )
        is not None
    )


def validate_test(
    test: PromptTest,
    compiled,
    plan,
) -> list[str]:
    failures: list[str] = []

    expected = test.expected

    decision = value(
        compiled,
        "decision",
        "unknown",
    )

    sql = normalize_sql(
        value(
            compiled,
            "sql",
        )
    )

    # --------------------------------------------------
    # Decision validation
    # --------------------------------------------------

    if decision != expected.decision:
        failures.append(
            (
                "Decision mismatch: "
                f"expected '{expected.decision}', "
                f"got '{decision}'."
            )
        )

    # --------------------------------------------------
    # Plan-level semantic validation
    #
    # create_and_compile_sql() may return only the
    # compiled object. In that case plan is None.
    #
    # Never report missing entities/tables/filters
    # simply because the plan object was not returned.
    # --------------------------------------------------

    if plan is not None:

        entity_names = (
            extract_entity_names(
                plan
            )
        )

        for expected_entity in (
            expected.expected_entities
        ):
            if (
                expected_entity
                not in entity_names
            ):
                failures.append(
                    (
                        "Missing entity: "
                        f"{expected_entity}"
                    )
                )

        table_names = (
            extract_table_names(
                plan
            )
        )

        for expected_table in (
            expected.expected_tables
        ):
            if (
                expected_table
                not in table_names
            ):
                failures.append(
                    (
                        "Missing table: "
                        f"{expected_table}"
                    )
                )

        filter_columns = (
            extract_filter_columns(
                plan
            )
        )

        for expected_column in (
            expected.expected_filter_columns
        ):
            if (
                expected_column
                not in filter_columns
            ):
                failures.append(
                    (
                        "Missing filter column: "
                        f"{expected_column}"
                    )
                )

        group_columns = (
            extract_group_by_columns(
                plan
            )
        )

        for expected_column in (
            expected.expected_group_by_columns
        ):
            if (
                expected_column
                not in group_columns
            ):
                failures.append(
                    (
                        "Missing GROUP BY column: "
                        f"{expected_column}"
                    )
                )

        if (
            expected.expected_join_ready
            is not None
        ):
            actual = (
                semantic_join_ready(
                    plan
                )
            )

            if (
                actual
                != expected.expected_join_ready
            ):
                failures.append(
                    (
                        "Join readiness mismatch: "
                        f"expected "
                        f"{expected.expected_join_ready}, "
                        f"got {actual}."
                    )
                )

        if (
            expected.expect_aggregation
            is not None
        ):
            actual = (
                aggregation_present(
                    plan
                )
            )

            if (
                actual
                != expected.expect_aggregation
            ):
                failures.append(
                    (
                        "Aggregation mismatch: "
                        f"expected "
                        f"{expected.expect_aggregation}, "
                        f"got {actual}."
                    )
                )

    # --------------------------------------------------
    # SQL semantic validation
    #
    # This still works even when the plan object
    # is not returned.
    # --------------------------------------------------

    for fragment in (
        expected.must_contain_sql
    ):
        if (
            fragment.lower()
            not in sql.lower()
        ):
            failures.append(
                (
                    "SQL missing expected "
                    f"fragment: {fragment}"
                )
            )

    for fragment in (
        expected.must_not_contain_sql
    ):
        if (
            fragment.lower()
            in sql.lower()
        ):
            failures.append(
                (
                    "SQL contains forbidden "
                    f"fragment: {fragment}"
                )
            )

    return failures


def run_test(
    database,
    test: PromptTest,
):
    try:
        result = (
            create_and_compile_sql(
                database=database,
                prompt=test.prompt,
                domain_id=None,
                requested_limit=100,
                maximum_entities=6,
                maximum_path_depth=4,
                user_role="analyst",
            )
        )

        compiled = value(
            result,
            "compiled",
            result,
        )

        plan = value(
            result,
            "plan",
        )

        decision = value(
            compiled,
            "decision",
            "unknown",
        )

        errors = value(
            compiled,
            "errors",
            [],
        ) or []

        warnings = value(
            compiled,
            "warnings",
            [],
        ) or []

        sql = value(
            compiled,
            "sql",
        )

        failures = validate_test(
            test=test,
            compiled=compiled,
            plan=plan,
        )

        success = (
            len(failures) == 0
        )

        print()
        print("=" * 78)

        print(
            (
                "PASS  "
                if success
                else "FAIL  "
            )
            + test.name
        )

        print(
            f"PROMPT: {test.prompt}"
        )

        print(
            f"DECISION: {decision}"
        )

        if plan is not None:
            print(
                "ENTITIES:",
                ", ".join(
                    extract_entity_names(
                        plan
                    )
                )
                or "-",
            )
        else:
            print(
                "PLAN DETAILS: "
                "Not returned by compiler wrapper"
            )

            print(
                "TABLES:",
                ", ".join(
                    extract_table_names(
                        plan
                    )
                )
                or "-",
            )

            print(
                "FILTER COLUMNS:",
                ", ".join(
                    extract_filter_columns(
                        plan
                    )
                )
                or "-",
            )

            print(
                "GROUP BY:",
                ", ".join(
                    extract_group_by_columns(
                        plan
                    )
                )
                or "-",
            )

            print(
                "JOIN READY:",
                semantic_join_ready(
                    plan
                ),
            )

            print(
                "AGGREGATION:",
                aggregation_present(
                    plan
                ),
            )

        if failures:
            print(
                "SEMANTIC FAILURES:"
            )

            for failure in failures:
                print(
                    f"  - {failure}"
                )

        if errors:
            print("COMPILER ERRORS:")

            for error in errors:
                print(
                    f"  - {error}"
                )

        if warnings:
            print("WARNINGS:")

            for warning in warnings:
                print(
                    f"  - {warning}"
                )

        if sql:
            print("SQL:")
            print(sql)

        return success

    except Exception as exc:
        print()
        print("=" * 78)

        print(
            f"ERROR {test.name}"
        )

        print(
            f"PROMPT: {test.prompt}"
        )

        print(
            (
                "EXCEPTION: "
                f"{type(exc).__name__}: "
                f"{exc}"
            )
        )

        return False


def main():
    database = SessionLocal()

    passed = 0
    failed = 0

    try:
        for test in TESTS:
            success = run_test(
                database,
                test,
            )

            if success:
                passed += 1
            else:
                failed += 1

    finally:
        database.close()

    total = (
        passed + failed
    )

    print()
    print("=" * 78)
    print(
        "NIBGPT FLEET SEMANTIC "
        "REGRESSION SUMMARY"
    )
    print("=" * 78)

    print(
        f"TOTAL : {total}"
    )

    print(
        f"PASS  : {passed}"
    )

    print(
        f"FAIL  : {failed}"
    )

    if total:
        percentage = round(
            passed
            / total
            * 100,
            1,
        )

        print(
            f"RATE  : {percentage}%"
        )

    print("=" * 78)


if __name__ == "__main__":
    main()