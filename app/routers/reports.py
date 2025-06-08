from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from datetime import datetime, timedelta

from app.dependencies import (
    get_database,
    get_current_user,
    validate_pagination,
    validate_date_range,
    analytics_rate_limiter
)
from app.models.report import Report, ReportStatus, ReportType
from app.models.company import Company
from app.models.product import Product
from app.models.datapoint import DataPoint
from app.schemas.report import (
    ReportCreate,
    ReportUpdate,
    ReportResponse,
    ReportDetailResponse,
    ReportListResponse,
    ReportGenerationRequest,
    QuickStatsResponse,
    DashboardData,
    PriceTrendData,
    SentimentTrendData,
    CompetitorAnalysisData,
    ReportExportRequest,
    ReportExportResponse
)
from app.services.report_service import ReportService
from app.services.analytics_service import AnalyticsService

router = APIRouter()

# Initialize services
report_service = ReportService()
analytics_service = AnalyticsService()

@router.get("/", response_model=ReportListResponse)
async def get_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    report_type: Optional[ReportType] = Query(None),
    status: Optional[ReportStatus] = Query(None),
    client_id: Optional[int] = Query(None),
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(analytics_rate_limiter)
):
    """
    Get list of reports with optional filtering.
    
    - **skip**: Number of reports to skip (pagination)
    - **limit**: Maximum number of reports to return
    - **report_type**: Filter by report type
    - **status**: Filter by report status
    - **client_id**: Filter by client ID
    """
    
    # Build query filters
    filters = []
    
    if report_type:
        filters.append(Report.report_type == report_type)
    
    if status:
        filters.append(Report.status == status)
    
    if client_id:
        filters.append(Report.client_id == client_id)
    
    # Execute query
    query = db.query(Report)
    
    if filters:
        query = query.filter(and_(*filters))
    
    total = query.count()
    reports = query.order_by(desc(Report.created_at)).offset(skip).limit(limit).all()
    
    return ReportListResponse(
        reports=[ReportResponse.from_orm(report) for report in reports],
        total=total,
        skip=skip,
        limit=limit
    )

@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: ReportCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(analytics_rate_limiter)
):
    """
    Create a new report.
    
    The report will be generated asynchronously in the background.
    """
    
    # Create report record
    report = Report(
        title=report_data.title,
        report_type=report_data.report_type,
        client_id=report_data.client_id,
        format=report_data.format,
        status=ReportStatus.PENDING,
        scheduled_for=report_data.scheduled_for
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Schedule report generation
    background_tasks.add_task(
        report_service.generate_report,
        report.id,
        {
            "companies": report_data.companies,
            "products": report_data.products,
            "date_range": report_data.date_range,
            "filters": report_data.filters
        }
    )
    
    return ReportResponse.from_orm(report)

@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: int,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(analytics_rate_limiter)
):
    """
    Get detailed information about a specific report.
    """
    
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Convert to detailed response
    report_detail = ReportDetailResponse.from_orm(report)
    
    # Add metadata if report is completed
    if report.status == ReportStatus.COMPLETED and report.content:
        report_detail.metadata = report.content.get("metadata", {})
        report_detail.summary = report.content.get("summary", {})
        report_detail.charts_data = report.content.get("charts_data", [])
    
    return report_detail

@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: int,
    report_data: ReportUpdate,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Update an existing report.
    """
    
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Update fields
    update_data = report_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(report, field, value)
    
    db.commit()
    db.refresh(report)
    
    return ReportResponse.from_orm(report)

@router.delete("/{report_id}")
async def delete_report(
    report_id: int,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a report.
    """
    
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    db.delete(report)
    db.commit()
    
    return {"message": "Report deleted successfully"}

@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportGenerationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(analytics_rate_limiter)
):
    """
    Generate a new report immediately.
    
    This endpoint creates a report and starts generation immediately.
    """
    
    # Create report record
    report = Report(
        title=request.title,
        report_type=request.report_type,
        client_id=current_user.get("id"),
        format=request.format,
        status=ReportStatus.PENDING
    )
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # Start report generation
    background_tasks.add_task(
        report_service.generate_report,
        report.id,
        {
            "companies": request.companies,
            "products": request.products,
            "metrics": request.metrics,
            "date_range": request.date_range
        }
    )
    
    return ReportResponse.from_orm(report)

@router.get("/dashboard/stats", response_model=QuickStatsResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(analytics_rate_limiter)
):
    """
    Get quick statistics for dashboard.
    """
    
    # Get counts
    total_companies = db.query(Company).filter(Company.is_active == True).count()
    total_products = db.query(Product).filter(Product.is_active == True).count()
    total_data_points = db.query(DataPoint).count()
    
    # Get last update time
    last_datapoint = db.query(DataPoint).order_by(desc(DataPoint.created_at)).first()
    last_update = last_datapoint.created_at if last_datapoint else None
    
    # Mock active scrapers count (in real implementation, get from Redis/Celery)
    active_scrapers = 3
    
    return QuickStatsResponse(
        total_companies=total_companies,
        total_products=total_products,
        total_data_points=total_data_points,
        last_update=last_update,
        active_scrapers=active_scrapers
    )

@router.get("/dashboard/data", response_model=DashboardData)
async def get_dashboard_data(
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user),
    _: bool = Depends(analytics_rate_limiter)
):
    """
    Get comprehensive dashboard data including trends and analysis.
    """
    
    # Get quick stats
    quick_stats = await get_dashboard_stats(db, current_user, _)
    
    # Get price trends (last 7 days)
    price_trends = await analytics_service.get_price_trends(db, days=7, limit=10)
    
    # Get sentiment trends
    sentiment_trends = await analytics_service.get_sentiment_trends(db, days=7, limit=10)
    
    # Get competitor analysis
    competitor_analysis = await analytics_service.get_competitor_analysis(db, limit=5)
    
    # Get recent alerts (mock data for now)
    recent_alerts = [
        {
            "id": 1,
            "type": "price_drop",
            "message": "iPhone 15 price dropped by 5% on Amazon",
            "created_at": datetime.now() - timedelta(hours=2)
        },
        {
            "id": 2,
            "type": "sentiment_change",
            "message": "Positive sentiment increase for Samsung Galaxy S24",
            "created_at": datetime.now() - timedelta(hours=6)
        }
    ]
    
    return DashboardData(
        quick_stats=quick_stats,
        price_trends=price_trends,
        sentiment_trends=sentiment_trends,
        competitor_analysis=competitor_analysis,
        recent_alerts=recent_alerts
    )

@router.post("/export", response_model=ReportExportResponse)
async def export_report(
    request: ReportExportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Export a report in the specified format.
    """
    
    report = db.query(Report).filter(Report.id == request.report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    if report.status != ReportStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report must be completed before export"
        )
    
    # Generate export URL (in real implementation, this would create a temporary file)
    export_url = f"/api/v1/reports/{request.report_id}/download/{request.format.value}"
    expires_at = datetime.now() + timedelta(hours=24)
    
    return ReportExportResponse(
        download_url=export_url,
        expires_at=expires_at,
        file_size=None  # Would be calculated in real implementation
    )

@router.get("/{report_id}/status")
async def get_report_status(
    report_id: int,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Get the current status of a report generation.
    """
    
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    progress_info = {
        "status": report.status,
        "progress": 0,
        "message": "Report generation pending"
    }
    
    if report.status == ReportStatus.PROCESSING:
        progress_info["progress"] = 50
        progress_info["message"] = "Report generation in progress"
    elif report.status == ReportStatus.COMPLETED:
        progress_info["progress"] = 100
        progress_info["message"] = "Report generation completed"
    elif report.status == ReportStatus.FAILED:
        progress_info["progress"] = 0
        progress_info["message"] = "Report generation failed"
    
    return progress_info

@router.post("/{report_id}/regenerate")
async def regenerate_report(
    report_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_database),
    current_user: dict = Depends(get_current_user)
):
    """
    Regenerate an existing report with fresh data.
    """
    
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    # Reset report status
    report.status = ReportStatus.PENDING
    report.generated_at = None
    report.content = None
    
    db.commit()
    
    # Schedule regeneration
    background_tasks.add_task(
        report_service.generate_report,
        report.id,
        {}  # Use default parameters
    )
    
    return {"message": "Report regeneration started"}
