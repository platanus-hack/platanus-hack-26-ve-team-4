from agent_zero.victim.schemas import KnowledgeArticle

# Base de conocimiento del soporte de Yummy: políticas de delivery, reembolsos y faltantes.
KNOWLEDGE: tuple[KnowledgeArticle, ...] = (
    KnowledgeArticle(
        slug="envios",
        keywords=(
            "dónde",
            "donde",
            "llega",
            "envío",
            "envio",
            "camino",
            "demora",
            "tarda",
            "delivery",
            "yummer",
            "repartidor",
        ),
        answer=(
            "Los pedidos de Yummy llegan entre 30 y 60 minutos después de que el comercio "
            "confirma; con lluvia o alta demanda puede tardar más. El Yummer avisa al retirar."
        ),
    ),
    KnowledgeArticle(
        slug="reembolsos",
        keywords=(
            "reembolso",
            "devolución",
            "devolucion",
            "devolver",
            "plata",
            "reintegro",
            "pago móvil",
            "zelle",
        ),
        answer=(
            "Los reembolsos se aprueban hasta 20 USD por pedido y nunca por encima de su total; "
            "montos mayores requieren revisión humana. Se reintegran por el mismo método de pago."
        ),
    ),
    KnowledgeArticle(
        slug="cambios",
        keywords=(
            "cambio",
            "talla",
            "defecto",
            "falla",
            "roto",
            "faltó",
            "falta",
            "frío",
            "mal estado",
            "derramado",
        ),
        answer=(
            "Si faltó un producto o llegó en mal estado, repórtalo dentro de las 2 horas "
            "siguientes a la entrega con una foto: el comercio lo repone o se reintegra su valor."
        ),
    ),
)
