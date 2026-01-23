"""Default prompt templates for spell generation."""

# System prompt for Claude - sets the context and persona (original, more whimsical)
SYSTEM_PROMPT = """You are a mystical spell crafter and spiritual guide who creates \
personalized magical spells and rituals. Your tone is warm, mystical, and encouraging. \
You write in an enchanting style that makes customers feel special and cared for.

Your spells should:
- Be personalized to the customer's specific intention
- Use poetic, mystical language
- Include practical ritual elements when appropriate
- Feel authentic and meaningful
- Be positive and empowering

Never include disclaimers about magic not being real. Maintain the mystical atmosphere throughout."""

# Revised system prompt for customer-cast spells - shorter, more professional tone
SYSTEM_PROMPT_CUSTOMER_CAST = """You are a professional spiritual guide who creates \
personalized spell casting instructions. Your tone is warm, professional, and supportive \
without being overly mystical or whimsical. You provide clear, practical guidance.

Your spell instructions should:
- Be personalized to the customer's specific intention
- Use professional, accessible language (avoid excessive mystical flourishes)
- Include clear, step-by-step ritual instructions
- Be encouraging but grounded
- Focus on practical actions the customer can take

Keep instructions clear and concise. Do not include disclaimers about magic."""

# Default prompt template used when spell_type has no custom template
DEFAULT_PROMPT_TEMPLATE = """Create a personalized spell for {{ customer_name }}.

**Spell Type:** {{ spell_type }}

**Customer's Intention:**
{{ intention }}

{% if personalization %}
**Additional Details from Customer:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Please create a beautiful, personalized spell that:
1. Opens with a warm greeting using their name
2. Acknowledges their specific intention
3. Provides the spell text with mystical language
4. Includes simple ritual instructions (candle, meditation, etc.)
5. Closes with words of encouragement

The spell should be approximately 300-500 words."""

# Template for love/romance spells
LOVE_SPELL_TEMPLATE = """Create a personalized love spell for {{ customer_name }}.

**Their Heart's Desire:**
{{ intention }}

{% if personalization %}
**Details They've Shared:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Craft a beautiful love spell that:
1. Opens with a warm, intimate greeting
2. Honors their desire for love and connection
3. Includes rose or heart imagery
4. Provides a candle ritual for attracting love
5. Emphasizes self-love as the foundation
6. Closes with blessings for their romantic journey

Use romantic, flowing language. Approximately 300-500 words."""

# Template for prosperity/abundance spells
PROSPERITY_SPELL_TEMPLATE = """Create a personalized prosperity spell for {{ customer_name }}.

**Their Abundance Goal:**
{{ intention }}

{% if personalization %}
**Specific Details:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Craft an empowering prosperity spell that:
1. Opens with an energizing greeting
2. Acknowledges their specific financial or abundance goals
3. Includes imagery of growth, gold, and flowing abundance
4. Provides a green candle or coin ritual
5. Emphasizes their worthiness to receive
6. Closes with affirmations of incoming prosperity

Use confident, abundant language. Approximately 300-500 words."""

# Template for protection spells
PROTECTION_SPELL_TEMPLATE = """Create a personalized protection spell for {{ customer_name }}.

**What They Seek Protection From:**
{{ intention }}

{% if personalization %}
**Additional Context:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Craft a powerful protection spell that:
1. Opens with a reassuring, strong greeting
2. Acknowledges their need for safety and boundaries
3. Includes imagery of shields, light, and sacred space
4. Provides a salt or black candle ritual
5. Emphasizes their inner strength
6. Closes with words of empowerment and safety

Use strong, protective language. Approximately 300-500 words."""

# Template for healing spells
HEALING_SPELL_TEMPLATE = """Create a personalized healing spell for {{ customer_name }}.

**Their Healing Intention:**
{{ intention }}

{% if personalization %}
**Details They've Shared:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Craft a gentle healing spell that:
1. Opens with a compassionate, soothing greeting
2. Acknowledges their journey toward healing
3. Includes imagery of light, water, and renewal
4. Provides a meditation or bath ritual
5. Emphasizes the body's natural healing wisdom
6. Closes with blessings for wholeness

Use gentle, nurturing language. Approximately 300-500 words."""

# Map of spell type slugs to their templates
SPELL_TYPE_TEMPLATES = {
    "love": LOVE_SPELL_TEMPLATE,
    "romance": LOVE_SPELL_TEMPLATE,
    "prosperity": PROSPERITY_SPELL_TEMPLATE,
    "abundance": PROSPERITY_SPELL_TEMPLATE,
    "money": PROSPERITY_SPELL_TEMPLATE,
    "protection": PROTECTION_SPELL_TEMPLATE,
    "healing": HEALING_SPELL_TEMPLATE,
    "health": HEALING_SPELL_TEMPLATE,
}

# ============================================================================
# CUSTOMER CAST TEMPLATES - Shorter, more professional tone (300-400 words)
# Used when cast_type is CUSTOMER_CAST or COMBINATION
# ============================================================================

# Default customer-cast template - professional, concise
CUSTOMER_CAST_DEFAULT_TEMPLATE = """Create concise spell casting instructions for {{ customer_name }}.

**Spell Type:** {{ spell_type }}

**Their Intention:**
{{ intention }}

{% if personalization %}
**Additional Details:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Write practical spell instructions that include:
1. A brief, warm greeting using their name
2. Acknowledge their intention in 1-2 sentences
3. List required materials (keep simple: candle, paper, quiet space)
4. Step-by-step casting instructions (5-7 clear steps)
5. Brief closing encouragement

Keep total length between 300-400 words. Be professional and supportive."""

# Customer-cast love spell template
CUSTOMER_CAST_LOVE_TEMPLATE = """Create concise love spell instructions for {{ customer_name }}.

**Their Heart's Desire:**
{{ intention }}

{% if personalization %}
**Details:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Write practical love spell instructions:
1. Brief greeting
2. Acknowledge their desire for love/connection
3. Materials: pink or red candle, paper, pen, quiet space
4. Clear steps (5-7 steps) for the ritual
5. Emphasize self-love as the foundation
6. Brief closing encouragement

Keep between 300-400 words. Professional, warm tone."""

# Customer-cast prosperity spell template
CUSTOMER_CAST_PROSPERITY_TEMPLATE = """Create concise prosperity spell instructions for {{ customer_name }}.

**Their Goal:**
{{ intention }}

{% if personalization %}
**Details:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Write practical prosperity spell instructions:
1. Brief greeting
2. Acknowledge their abundance goals
3. Materials: green candle, a coin, paper, pen
4. Clear steps (5-7 steps) for the ritual
5. Emphasize taking action alongside the magic
6. Brief closing encouragement

Keep between 300-400 words. Confident, grounded tone."""

# Customer-cast protection spell template
CUSTOMER_CAST_PROTECTION_TEMPLATE = """Create concise protection spell instructions for {{ customer_name }}.

**What They Seek Protection From:**
{{ intention }}

{% if personalization %}
**Context:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Write practical protection spell instructions:
1. Brief, reassuring greeting
2. Acknowledge their need for protection/boundaries
3. Materials: white or black candle, salt, quiet space
4. Clear steps (5-7 steps) for the ritual
5. Emphasize their inner strength
6. Brief closing with words of safety

Keep between 300-400 words. Strong, supportive tone."""

# Customer-cast healing spell template
CUSTOMER_CAST_HEALING_TEMPLATE = """Create concise healing spell instructions for {{ customer_name }}.

**Their Healing Intention:**
{{ intention }}

{% if personalization %}
**Details:**
{% for key, value in personalization.items() %}
- {{ key }}: {{ value }}
{% endfor %}
{% endif %}

Write practical healing spell instructions:
1. Brief, compassionate greeting
2. Acknowledge their healing journey
3. Materials: blue or white candle, water, comfortable space
4. Clear steps (5-7 steps) including breathing/meditation
5. Emphasize patience and self-compassion
6. Brief closing with blessings for wholeness

Keep between 300-400 words. Gentle, nurturing tone."""

# Map of spell type slugs to customer-cast templates
CUSTOMER_CAST_TEMPLATES = {
    "love": CUSTOMER_CAST_LOVE_TEMPLATE,
    "romance": CUSTOMER_CAST_LOVE_TEMPLATE,
    "prosperity": CUSTOMER_CAST_PROSPERITY_TEMPLATE,
    "abundance": CUSTOMER_CAST_PROSPERITY_TEMPLATE,
    "money": CUSTOMER_CAST_PROSPERITY_TEMPLATE,
    "protection": CUSTOMER_CAST_PROTECTION_TEMPLATE,
    "healing": CUSTOMER_CAST_HEALING_TEMPLATE,
    "health": CUSTOMER_CAST_HEALING_TEMPLATE,
}


def get_customer_cast_template(slug: str) -> str:
    """Get the customer-cast template for a spell type.

    These templates produce shorter, more professional output (300-400 words).

    Args:
        slug: The spell type slug (e.g., 'love', 'prosperity')

    Returns:
        The customer-cast template string, or CUSTOMER_CAST_DEFAULT_TEMPLATE if no match
    """
    return CUSTOMER_CAST_TEMPLATES.get(slug.lower(), CUSTOMER_CAST_DEFAULT_TEMPLATE)


def get_template_for_spell_type(slug: str) -> str:
    """Get the appropriate template for a spell type.

    Args:
        slug: The spell type slug (e.g., 'love', 'prosperity')

    Returns:
        The template string, or DEFAULT_PROMPT_TEMPLATE if no match
    """
    return SPELL_TYPE_TEMPLATES.get(slug.lower(), DEFAULT_PROMPT_TEMPLATE)


# Documentation of available template variables
TEMPLATE_VARIABLES = """
Available variables for prompt templates:

{{ customer_name }} - The customer's name from the order
{{ intention }} - The customer's stated intention/wish
{{ spell_type }} - Name of the spell type (e.g., "Love Spell")
{{ spell_type_slug }} - URL-friendly slug (e.g., "love-spell")
{{ personalization }} - Dict of custom fields from Etsy order variations
{{ order_date }} - When the order was placed (formatted date string)
{{ order_id }} - Internal order ID

Jinja2 syntax is supported:
- {{ variable }} - Output a variable
- {% if condition %}...{% endif %} - Conditional blocks
- {% for item in list %}...{% endfor %} - Loops
- {{ variable | default('fallback') }} - Default values
"""
