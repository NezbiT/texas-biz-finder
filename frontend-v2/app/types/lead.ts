/** Un negocio (lead) tal como lo devuelve la API FastAPI (/api/leads). */
export interface Lead {
  id: number                              // id interno de la base
  external_id: string                     // taxpayer number del Comptroller de Texas
  name: string                            // razón social / nombre del negocio
  city: string                            // ciudad
  county: string | null                   // condado
  state: string                           // estado (siempre TX)
  zip_code: string | null                 // código postal
  latitude: number | null                 // coordenadas (si se geocodificó)
  longitude: number | null
  distance_miles: number | null           // distancia al centro de búsqueda por radio
  phone: string | null                    // teléfono de contacto
  email: string | null                    // email de contacto
  industry: string | null                 // industria/giro del negocio
  employee_count: number | null           // nº de empleados (si se conoce)
  website_url: string | null              // URL del sitio web detectado/guardado
  has_website: boolean                    // ¿tiene sitio web?
  website_reachable: boolean              // ¿el sitio responde?
  has_modern_website: boolean             // ¿el sitio parece moderno? (análisis)
  website_tech_stack: string | null       // tecnologías detectadas (WordPress…)
  website_antiquity_years: number | null  // antigüedad estimada del sitio (años)
  website_analysis_notes: string | null   // notas del análisis (incluye marca TABC)
  facebook_url: string | null             // redes sociales detectadas
  instagram_url: string | null
  has_active_facebook: boolean            // ¿la página de FB parece activa?
  has_active_instagram: boolean
  is_small_business: boolean              // ¿clasificado como negocio pequeño?
  is_qualified: boolean                   // ¿lead calificado? (score sobre umbral)
  qualification_score: number             // puntaje de calificación (0-100)
  qualification_notes: string | null      // por qué calificó / no calificó
  sells_alcohol?: boolean                 // cruce TABC mixed beverage
  source: string                          // origen del dato (franchise, TABC…)
  created_at: string                      // timestamps ISO
  updated_at: string
}
