from app.extensions import db


class EmployeeUKTaxProfile(db.Model):
    __tablename__ = "employee_uk_tax_profiles"

    TAX_BASES = ("CUMULATIVE", "W1_M1")
    TAX_REGIONS = ("ENGLAND_NI", "SCOTLAND", "WALES")
    NI_METHODS = ("STANDARD", "ALTERNATIVE")
    STUDENT_LOAN_PLANS = ("NONE", "PLAN_1", "PLAN_2", "PLAN_4", "PLAN_5")

    id = db.Column(db.Integer, primary_key=True)

    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    tax_code = db.Column(
        db.String(20),
        nullable=False,
        default="1257L",
        server_default="1257L",
    )

    tax_basis = db.Column(
        db.String(20),
        nullable=False,
        default="CUMULATIVE",
        server_default="CUMULATIVE",
    )

    tax_region = db.Column(
        db.String(20),
        nullable=False,
        default="ENGLAND_NI",
        server_default="ENGLAND_NI",
    )

    ni_category = db.Column(
        db.String(2),
        nullable=False,
        default="A",
        server_default="A",
    )

    is_director = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    director_ni_method = db.Column(
        db.String(20),
        nullable=False,
        default="STANDARD",
        server_default="STANDARD",
    )

    student_loan_plan = db.Column(
        db.String(20),
        nullable=False,
        default="NONE",
        server_default="NONE",
    )

    postgraduate_loan = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=db.false(),
    )

    employee = db.relationship(
        "Employee",
        back_populates="uk_tax_profile",
    )

    __table_args__ = (
        db.CheckConstraint(
            "tax_basis IN ('CUMULATIVE', 'W1_M1')",
            name="ck_employee_uk_tax_profiles_tax_basis",
        ),
        db.CheckConstraint(
            "tax_region IN ('ENGLAND_NI', 'SCOTLAND', 'WALES')",
            name="ck_employee_uk_tax_profiles_tax_region",
        ),
        db.CheckConstraint(
            "char_length(ni_category) BETWEEN 1 AND 2",
            name="ck_employee_uk_tax_profiles_ni_category_length",
        ),
        db.CheckConstraint(
            "director_ni_method IN ('STANDARD', 'ALTERNATIVE')",
            name="ck_employee_uk_tax_profiles_director_ni_method",
        ),
        db.CheckConstraint(
            """
            student_loan_plan IN
            ('NONE', 'PLAN_1', 'PLAN_2', 'PLAN_4', 'PLAN_5')
            """,
            name="ck_employee_uk_tax_profiles_student_loan_plan",
        ),
    )

    def __repr__(self):
        return (
            f"<EmployeeUKTaxProfile employee_id={self.employee_id} "
            f"tax_code={self.tax_code}>"
        )
