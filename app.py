"""
app.py — Main Flask application for NetSage AI
AI-Assisted Network Troubleshooting with Human Review
"""
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort

from config import Config
from database.database import db, init_db
from database.models import Case, Diagnosis, Review, RuleResult
from services.diagnosis_service import run_diagnosis, get_diagnosis_with_review_status
from services.review_service import save_review, get_review_stats, get_responsible_ai_log, get_all_reviews

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_class=Config):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize DB
    init_db(app)

    # ─── TEMPLATE FILTERS ───────────────────────────────────────────────────────

    @app.template_filter("from_json")
    def from_json_filter(value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return [str(value)]

    @app.template_filter("badge_color")
    def badge_color_filter(value):
        mapping = {
            "HIGH": "badge-high",
            "MEDIUM": "badge-medium",
            "LOW": "badge-low",
            "CRITICAL": "badge-critical",
            "PASS": "badge-pass",
            "FAIL": "badge-fail",
            "WARNING": "badge-warning",
            "NOT_CHECKED": "badge-nc",
            "ACCEPT": "badge-accept",
            "ACCEPTED": "badge-accept",
            "EDIT": "badge-edit",
            "EDITED": "badge-edit",
            "REJECT": "badge-reject",
            "REJECTED": "badge-reject",
            "PENDING": "badge-pending",
            "DEMO": "badge-demo",
            "LIVE": "badge-live",
            "AGREE": "badge-pass",
            "PARTIAL": "badge-warning",
            "DISAGREE": "badge-fail",
        }
        return mapping.get(str(value).upper(), "badge-default")

    # ─── CONTEXT PROCESSORS ─────────────────────────────────────────────────────

    @app.context_processor
    def inject_globals():
        return {
            "demo_mode": app.config.get("DEMO_MODE", True),
            "app_name": "NetSage AI",
        }

    # ─── ERROR HANDLERS ─────────────────────────────────────────────────────────

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", error_code=404, message="Page not found."), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        return render_template("error.html", error_code=500, message="Internal server error."), 500

    # ─── ROUTES ─────────────────────────────────────────────────────────────────

    @app.route("/")
    def dashboard():
        """Dashboard with statistics and charts."""
        try:
            stats = get_review_stats()
            total_cases = Case.query.count()

            # Category distribution
            categories = ["VLAN", "Gateway", "DHCP", "DNS", "Routing", "ACL", "NAT", "Wireless"]
            category_counts = {}
            for cat in categories:
                category_counts[cat] = Case.query.filter_by(category=cat).count()

            # Severity distribution
            severity_counts = {
                "Low": Case.query.filter_by(severity="Low").count(),
                "Medium": Case.query.filter_by(severity="Medium").count(),
                "High": Case.query.filter_by(severity="High").count(),
                "Critical": Case.query.filter_by(severity="Critical").count(),
            }

            # Recent cases
            recent_cases = Case.query.order_by(Case.created_at.desc()).limit(6).all()

            # Recent reviews
            recent_reviews = (
                Review.query.order_by(Review.created_at.desc()).limit(5).all()
            )

            return render_template(
                "dashboard.html",
                stats=stats,
                total_cases=total_cases,
                category_counts=category_counts,
                severity_counts=severity_counts,
                recent_cases=recent_cases,
                recent_reviews=recent_reviews,
            )
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            return render_template("error.html", error_code=500, message=str(e)), 500

    @app.route("/cases")
    def cases():
        """List all cases with filtering and search."""
        search = request.args.get("search", "").strip()
        category = request.args.get("category", "").strip()
        severity = request.args.get("severity", "").strip()
        osi = request.args.get("osi", "").strip()

        query = Case.query

        if search:
            like = f"%{search}%"
            query = query.filter(
                db.or_(
                    Case.title.ilike(like),
                    Case.symptom.ilike(like),
                    Case.case_id.ilike(like),
                    Case.expected_fault.ilike(like),
                )
            )
        if category:
            query = query.filter_by(category=category)
        if severity:
            query = query.filter_by(severity=severity)
        if osi:
            query = query.filter(Case.osi_layer.ilike(f"%{osi}%"))

        all_cases = query.order_by(Case.case_id).all()

        # Get review status for each case
        case_review_status = {}
        for c in all_cases:
            latest_diag = (
                Diagnosis.query.filter_by(case_id=c.case_id)
                .order_by(Diagnosis.created_at.desc())
                .first()
            )
            if latest_diag and latest_diag.review:
                case_review_status[c.case_id] = latest_diag.review.decision
            elif latest_diag:
                case_review_status[c.case_id] = "PENDING"
            else:
                case_review_status[c.case_id] = None

        categories = ["VLAN", "Gateway", "DHCP", "DNS", "Routing", "ACL", "NAT", "Wireless"]
        osi_layers = ["Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 7"]

        return render_template(
            "cases.html",
            cases=all_cases,
            case_review_status=case_review_status,
            categories=categories,
            osi_layers=osi_layers,
            search=search,
            selected_category=category,
            selected_severity=severity,
            selected_osi=osi,
        )

    @app.route("/cases/<case_id>")
    def case_detail(case_id):
        """Case detail page."""
        case = Case.query.filter_by(case_id=case_id).first_or_404()
        latest_diagnosis = (
            Diagnosis.query.filter_by(case_id=case_id)
            .order_by(Diagnosis.created_at.desc())
            .first()
        )
        return render_template(
            "case_detail.html",
            case=case,
            latest_diagnosis=latest_diagnosis,
        )

    @app.route("/cases/<case_id>/diagnose", methods=["POST"])
    def diagnose_case(case_id):
        """Run AI diagnosis for a specific case."""
        case = Case.query.filter_by(case_id=case_id).first_or_404()
        try:
            result = run_diagnosis(case_id=case_id)
            return redirect(url_for("show_diagnosis", case_id=case_id, diagnosis_id=result["diagnosis_id"]))
        except Exception as e:
            logger.error(f"Diagnosis error for {case_id}: {e}")
            flash(f"Diagnosis failed: {str(e)}", "error")
            return redirect(url_for("case_detail", case_id=case_id))

    @app.route("/cases/<case_id>/diagnosis/<int:diagnosis_id>")
    def show_diagnosis(case_id, diagnosis_id):
        """Show diagnosis results."""
        case = Case.query.filter_by(case_id=case_id).first_or_404()
        diagnosis = Diagnosis.query.get_or_404(diagnosis_id)
        rule_results = (
            RuleResult.query.filter_by(case_id=case_id)
            .filter_by(diagnosis_id=diagnosis_id)
            .all()
        )
        if not rule_results:
            rule_results = (
                RuleResult.query.filter_by(case_id=case_id)
                .order_by(RuleResult.created_at.desc())
                .limit(9)
                .all()
            )

        # Compute overall assessment
        from services.diagnosis_service import _compute_overall_assessment
        from checker.rule_checker import get_rule_summary

        diag_dict = diagnosis.to_dict()
        rule_checks = [r.to_dict() for r in rule_results]
        rule_summary = get_rule_summary(rule_checks)
        overall = _compute_overall_assessment(diag_dict, rule_checks)

        return render_template(
            "diagnosis.html",
            case=case,
            diagnosis=diagnosis,
            diag_dict=diag_dict,
            rule_results=rule_results,
            rule_summary=rule_summary,
            overall=overall,
            existing_review=diagnosis.review,
        )

    @app.route("/cases/<case_id>/diagnosis/<int:diagnosis_id>/review", methods=["GET", "POST"])
    def review_diagnosis(case_id, diagnosis_id):
        """Human review of an AI diagnosis."""
        case = Case.query.filter_by(case_id=case_id).first_or_404()
        diagnosis = Diagnosis.query.get_or_404(diagnosis_id)

        if request.method == "POST":
            decision = request.form.get("decision", "").upper()
            if decision not in ("ACCEPT", "EDIT", "REJECT"):
                flash("Invalid decision. Please select Accept, Edit, or Reject.", "error")
                return redirect(url_for("review_diagnosis", case_id=case_id, diagnosis_id=diagnosis_id))

            # Validation
            if decision == "REJECT" and not request.form.get("reviewer_comment", "").strip():
                flash("A reviewer comment is required when rejecting a diagnosis.", "error")
                return redirect(url_for("review_diagnosis", case_id=case_id, diagnosis_id=diagnosis_id))

            try:
                review = save_review(
                    diagnosis_id=diagnosis_id,
                    decision=decision,
                    form_data=request.form.to_dict(),
                )
                flash(f"Review saved successfully. Decision: {decision}", "success")
                return redirect(url_for("show_diagnosis", case_id=case_id, diagnosis_id=diagnosis_id))
            except Exception as e:
                logger.error(f"Review save error: {e}")
                flash(f"Failed to save review: {str(e)}", "error")

        return render_template(
            "review.html",
            case=case,
            diagnosis=diagnosis,
            diag_dict=diagnosis.to_dict(),
            existing_review=diagnosis.review,
        )

    @app.route("/troubleshoot", methods=["GET", "POST"])
    def troubleshoot():
        """Custom troubleshooting — user enters their own problem."""
        if request.method == "POST":
            symptom = request.form.get("symptom", "").strip()
            topology = request.form.get("topology", "").strip()
            show_outputs = request.form.get("show_outputs", "").strip()
            category = request.form.get("category", "Other").strip()

            errors = []
            if not symptom:
                errors.append("Symptom description is required.")
            if not show_outputs:
                errors.append("At least some show command output is required for analysis.")

            if errors:
                for err in errors:
                    flash(err, "error")
                return render_template(
                    "troubleshoot.html",
                    form_data=request.form.to_dict(),
                )

            try:
                custom_input = {
                    "symptom": symptom,
                    "topology": topology,
                    "show_outputs": show_outputs,
                    "category": category,
                }
                result = run_diagnosis(custom_input=custom_input)

                return render_template(
                    "troubleshoot_result.html",
                    diagnosis=result["diagnosis"],
                    rule_checks=result["rule_checks"],
                    rule_summary=result["rule_summary"],
                    overall=result["overall_assessment"],
                    custom_input=custom_input,
                )
            except Exception as e:
                logger.error(f"Custom troubleshoot error: {e}")
                flash(f"Analysis failed: {str(e)}", "error")
                return render_template(
                    "troubleshoot.html",
                    form_data=request.form.to_dict(),
                )

        return render_template("troubleshoot.html", form_data={})

    @app.route("/reviews")
    def reviews():
        """All human reviews."""
        all_reviews = get_all_reviews()
        stats = get_review_stats()
        return render_template("reviews.html", reviews=all_reviews, stats=stats)

    @app.route("/responsible-ai")
    def responsible_ai():
        """Responsible AI page with correction examples."""
        corrections = get_responsible_ai_log()
        stats = get_review_stats()
        return render_template("responsible_ai.html", corrections=corrections, stats=stats)

    @app.route("/about")
    def about():
        """About page."""
        return render_template("about.html")

    # ─── API ENDPOINTS ───────────────────────────────────────────────────────────

    @app.route("/api/stats")
    def api_stats():
        """JSON stats endpoint for dashboard charts."""
        stats = get_review_stats()
        categories = ["VLAN", "Gateway", "DHCP", "DNS", "Routing", "ACL", "NAT", "Wireless"]
        category_counts = {cat: Case.query.filter_by(category=cat).count() for cat in categories}
        severity_counts = {
            "Low": Case.query.filter_by(severity="Low").count(),
            "Medium": Case.query.filter_by(severity="Medium").count(),
            "High": Case.query.filter_by(severity="High").count(),
            "Critical": Case.query.filter_by(severity="Critical").count(),
        }
        return jsonify({
            "stats": stats,
            "category_counts": category_counts,
            "severity_counts": severity_counts,
            "total_cases": Case.query.count(),
        })

    @app.route("/api/cases")
    def api_cases():
        """JSON cases list."""
        cases = Case.query.order_by(Case.case_id).all()
        return jsonify([c.to_dict() for c in cases])

    return app


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        from database.database import db
        db.create_all()
    print("=" * 60)
    print("  NetSage AI — Network Troubleshooting Assistant")
    print("=" * 60)
    print("  Starting Flask development server...")
    print("  Open: http://127.0.0.1:5000")
    print("  Press CTRL+C to stop")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
