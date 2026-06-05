from reportlab.lib.pagesizes import A6
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import mm
import os


PRIMARY_RED = colors.HexColor("#B71C1C")
PRIMARY_ORANGE = colors.HexColor("#F28C1B")
LIGHT_GREY = colors.HexColor("#F5F5F5")
DARK_TEXT = colors.HexColor("#222222")


def build_order_section(order, items, elements, styles):

    # ======================
    # STYLES
    # ======================

    title_style = ParagraphStyle(
        "title",
        parent=styles["Heading1"],
        fontName="Times-Bold",
        fontSize=14,
        alignment=TA_CENTER,
        textColor=PRIMARY_RED,
        leading=18,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        "subtitle",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=8,
        alignment=TA_CENTER,
        textColor=PRIMARY_ORANGE,
        spaceAfter=10
    )

    body_style = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontName="Times-Roman",
        fontSize=7,
        leading=10,
        textColor=DARK_TEXT
    )

    summary_style = ParagraphStyle(
        "summary",
        parent=body_style,
        fontName="Times-Bold",
        fontSize=6
    )

    # ======================
    # LOGO
    # ======================

    logo_path = "assets/Round-logo-of-Soni_PNG.png"

    header_data = []

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=22,
            height=22
        )

    else:
        logo = ""
        
    order_style = ParagraphStyle(
        "orderHeader",
        parent=styles["Heading1"],
        fontName="Times-Bold",
        fontSize=12,
        textColor=PRIMARY_RED,
        alignment=2,
        leading=14
    )

    # header_style = ParagraphStyle(
    #     "header",
    #     parent=styles["Heading1"],
    #     fontName="Times-Bold",
    #     fontSize=8,
    #     textColor=PRIMARY_RED,
    #     alignment=2
    # )

    order_number = Paragraph(
        f"Order #{order['order_number']}",
        order_style
    )

    header = Table(
        [
            [
                logo,
                order_number
            ]
        ],

        colWidths=[
            20*mm,
            70*mm
        ]
    )

    header.setStyle(
        TableStyle([

            (
                "VALIGN",
                (0,0),
                (-1,-1),
                "MIDDLE"
            ),

            (
                "ALIGN",
                (0,0),
                (0,0),
                "LEFT"
            ),

            (
                "ALIGN",
                (1,0),
                (1,0),
                "RIGHT"
            ),

            (
                "BOTTOMPADDING",
                (0,0),
                (-1,-1),
                4
            ),

            (
                "TOPPADDING",
                (0,0),
                (-1,-1),
                2
            ),

            (
                "LEFTPADDING",
                (0,0),
                (-1,-1),
                0
            ),

            (
                "RIGHTPADDING",
                (0,0),
                (-1,-1),
                0
            ),

            (
                "LINEBELOW",
                (0,0),
                (-1,0),
                1,
                PRIMARY_ORANGE
            )

        ])
    )

    elements.append(header)

    elements.append(
        Spacer(
            1,
            4
        )
    )
    # ======================
    # ORDER DETAILS
    # ======================

    details_data = [

        [
            "Order",
            order["order_number"],

            "Status / Invoice",

            f"{order['order_status']} / {order['invoice_status']}"
        ],

        [
            "Date",
            str(order["created_at"]).split(" ")[0],

            "Customer",
            order["business_name"]

            # (
            #     order["business_name"][:12] + ".."
            #     if len(order["business_name"]) > 12
            #     else order["business_name"]
            # )
        ],

        [
            "Region",
            order["region_name"],

            "Godown",

            order["godown_name"] if order["godown_name"] else order["godown_id"] if order["godown_id"] else "-"
        ],

        [
            "Agent",

            (
                order["sales_agent_name"][:10]
                if order["sales_agent_name"]
                else "-"
            ),

            "Mobile",

            order["sales_agent_mobile"]
        ]

    ]

    details_table = Table(

        details_data,

        colWidths=[
            15*mm,
            28*mm,
            15*mm,
            28*mm
        ]
    )

    details_table.setStyle(

        TableStyle([

            (
                "FONTNAME",
                (0,0),
                (-1,-1),
                "Times-Roman"
            ),

            (
                "FONTNAME",
                (0,0),
                (-1,-1),
                "Times-Bold"
            ),

            (
                "FONTNAME",
                (1,0),
                (-1,-1),
                "Times-Roman"
            ),

            (
                "FONTSIZE",
                (0,0),
                (-1,-1),
                6
            ),

            (
                "GRID",
                (0,0),
                (-1,-1),
                0.4,
                colors.grey
            ),

            (
                "BACKGROUND",
                (0,0),
                (0,-1),
                PRIMARY_RED
            ),

            (
                "BACKGROUND",
                (2,0),
                (2,-1),
                PRIMARY_RED
            ),

            (
                "TEXTCOLOR",
                (0,0),
                (0,-1),
                colors.white
            ),

            (
                "TEXTCOLOR",
                (2,0),
                (2,-1),
                colors.white
            ),

            (
                "VALIGN",
                (0,0),
                (-1,-1),
                "MIDDLE"
            ),

            (
                "TOPPADDING",
                (0,0),
                (-1,-1),
                2
            ),

            (
                "BOTTOMPADDING",
                (0,0),
                (-1,-1),
                2
            ),

            (
                "LEFTPADDING",
                (0,0),
                (-1,-1),
                3
            ),

            (
                "RIGHTPADDING",
                (0,0),
                (-1,-1),
                3
            )

        ])
    )

    elements.append(details_table)

    elements.append(
        Spacer(
            1,
            4
        )
    )

    # ======================
    # ITEMS TABLE
    # ======================

    table_data = [[
        "Product",
        "Qty",
        "Done",
        "Rate",
        "Total"
    ]]

    for item in items:

        product = item["product_name"]

        table_data.append([

            product,

            item["quantity"],

            item["fulfilled"],

            f"{int(item['price_per_unit'])}",

            f"{int(item['total_price'])}"

        ])
    table_data.append([

        "TOTAL",

        str(order["total_quantity"]),

        str(order["total_fulfilled"]),

        "",

        f"{float(order['total_amount']):,.0f}"

    ])
    
    table = Table(
        table_data,

        colWidths=[
            36*mm,
            8*mm,
            8*mm,
            14*mm,
            20*mm
        ],

        repeatRows=1
    )

    table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0,0),
                (-1,0),
                PRIMARY_RED
            ),

            (
                "TEXTCOLOR",
                (0,0),
                (-1,0),
                colors.white
            ),

            (
                "FONTNAME",
                (0,0),
                (-1,0),
                "Times-Bold"
            ),

            (
                "FONTNAME",
                (0,1),
                (-1,-1),
                "Times-Roman"
            ),

            (
                "FONTSIZE",
                (0,0),
                (-1,-1),
                5
            ),

            (
                "GRID",
                (0,0),
                (-1,-1),
                0.4,
                colors.grey
            ),

            (
                "ROWBACKGROUNDS",
                (0,1),
                (-1,-2),
                [
                    colors.white,
                    LIGHT_GREY
                ]
            ),

            # TOTAL ROW
            (
                "BACKGROUND",
                (0,-1),
                (-1,-1),
                PRIMARY_ORANGE
            ),

            (
                "TEXTCOLOR",
                (0,-1),
                (-1,-1),
                colors.white
            ),

            (
                "FONTNAME",
                (0,-1),
                (-1,-1),
                "Times-Bold"
            ),

            (
                "ALIGN",
                (1,1),
                (-1,-1),
                "CENTER"
            ),

            (
                "TOPPADDING",
                (0,0),
                (-1,-1),
                2
            ),

            (
                "BOTTOMPADDING",
                (0,0),
                (-1,-1),
                2
            ),

            (
                "LEFTPADDING",
                (0,0),
                (-1,-1),
                2
            ),

            (
                "RIGHTPADDING",
                (0,0),
                (-1,-1),
                2
            )

        ])
    )

    elements.append(table)

    # elements.append(Spacer(1, 10))

    # ======================
    # SUMMARY
    # ======================

    # summary_table = Table(
    #     [

    #         ["Items", order["total_items"]],

    #         ["Qty", order["total_quantity"]],

    #         ["Done", order["total_fulfilled"]],

    #         [
    #             "Amount",
    #             f"₹ {float(order['total_amount']):,.2f}"
    #         ]

    #     ],

    #     colWidths=[
    #         28*mm,
    #         55*mm
    #     ]
    # )

    # summary_table.setStyle(
    #     TableStyle([

    #         (
    #             "FONTNAME",
    #             (0,0),
    #             (-1,-1),
    #             "Times-Roman"
    #         ),

    #         (
    #             "FONTNAME",
    #             (0,0),
    #             (0,-1),
    #             "Times-Bold"
    #         ),

    #         (
    #             "FONTSIZE",
    #             (0,0),
    #             (-1,-1),
    #             7
    #         ),

    #         (
    #             "GRID",
    #             (0,0),
    #             (-1,-1),
    #             0.5,
    #             colors.grey
    #         ),

    #         (
    #             "BACKGROUND",
    #             (0,0),
    #             (0,-1),
    #             PRIMARY_ORANGE
    #         ),

    #         (
    #             "TEXTCOLOR",
    #             (0,0),
    #             (0,-1),
    #             colors.white
    #         ),

    #         (
    #             "TOPPADDING",
    #             (0,0),
    #             (-1,-1),
    #             4
    #         ),

    #         (
    #             "BOTTOMPADDING",
    #             (0,0),
    #             (-1,-1),
    #             4
    #         )
    #     ])
    # )

    # elements.append(summary_table)