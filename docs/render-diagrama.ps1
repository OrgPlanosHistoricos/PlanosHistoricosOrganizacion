Add-Type -AssemblyName System.Drawing
$dest = Join-Path $PWD 'docs/diagrama-clases.png'
$bmp = New-Object System.Drawing.Bitmap 3400,3200
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.TextRenderingHint = 'AntiAliasGridFit'
$g.Clear([System.Drawing.Color]::White)
$ink = [System.Drawing.ColorTranslator]::FromHtml('#172033')
$brush = New-Object System.Drawing.SolidBrush $ink
$blue = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#2148B5'))
$fill = New-Object System.Drawing.SolidBrush ([System.Drawing.ColorTranslator]::FromHtml('#F1F4FA'))
$pen = New-Object System.Drawing.Pen $ink,3
$titleFont = New-Object System.Drawing.Font 'Segoe UI',42,([System.Drawing.FontStyle]::Bold)
$headFont = New-Object System.Drawing.Font 'Segoe UI',24,([System.Drawing.FontStyle]::Bold)
$font = New-Object System.Drawing.Font 'Consolas',16
$small = New-Object System.Drawing.Font 'Segoe UI',20
function Txt($s,$x,$y,$f=$font) { $g.DrawString($s,$f,$brush,[single]$x,[single]$y) }
function Box($name,$x,$y,$w,$attrs,$methods=@()) {
 $rowH = 30
 $attrH = $attrs.Count * $rowH + 16
 $methH = if ($methods.Count -gt 0) { $methods.Count * $rowH + 20 } else { 0 }
 $h = 68 + $attrH + $methH
 $g.FillRectangle($fill,$x,$y,$w,68)
 $g.DrawRectangle($pen,$x,$y,$w,$h)
 $g.DrawLine($pen,$x,($y+68),($x+$w),($y+68))
 Txt $name ($x+20) ($y+14) $headFont
 for($i=0;$i -lt $attrs.Count;$i++){Txt $attrs[$i] ($x+18) ($y+76+$i*$rowH)}
 if ($methods.Count -gt 0) {
  $sepY = $y + 68 + $attrH
  $g.DrawLine($pen,$x,$sepY,($x+$w),$sepY)
  for($j=0;$j -lt $methods.Count;$j++){Txt $methods[$j] ($x+18) ($sepY+10+$j*$rowH)}
 }
}
function Line($x1,$y1,$x2,$y2){$g.DrawLine($pen,$x1,$y1,$x2,$y2)}
function Inherit($x1,$y,$x2){
 Line $x1 $y ($x2+24) $y
 $pts = [System.Drawing.Point[]]@([System.Drawing.Point]::new($x2,$y),[System.Drawing.Point]::new(($x2+24),($y-14)),[System.Drawing.Point]::new(($x2+24),($y+14)))
 $g.FillPolygon([System.Drawing.Brushes]::White,$pts)
 $g.DrawPolygon($pen,$pts)
}
$g.DrawString('DIAGRAMA DE CLASES / CATÁLOGO DE PLANOS',$small,$blue,70,40)
Txt 'Sistema de Organización de Planos Históricos' 70 80 $titleFont
Box 'DatosPlano' 70 200 620 @(
 '- texto_extraido: str?',
 '- arquitecto: str?',
 '- anio: int?',
 '- titulo: str?',
 '- ubicacion: str?',
 '- escala: str?',
 '- tipo_de_plano: str?',
 '- material_soporte: str?',
 '- notas: str?'
) @(
 '+ get_texto_extraido(): str?',
 '+ set_texto_extraido(valor: str?): void',
 '+ get_arquitecto(): str?',
 '+ set_arquitecto(valor: str?): void',
 '+ get_anio(): int?',
 '+ set_anio(valor: int?): void',
 '+ get_titulo(): str?',
 '+ set_titulo(valor: str?): void',
 '+ get_ubicacion(): str?',
 '+ set_ubicacion(valor: str?): void',
 '+ get_escala(): str?',
 '+ set_escala(valor: str?): void',
 '+ get_tipo_de_plano(): str?',
 '+ set_tipo_de_plano(valor: str?): void',
 '+ get_material_soporte(): str?',
 '+ set_material_soporte(valor: str?): void',
 '+ get_notas(): str?',
 '+ set_notas(valor: str?): void'
)
Box 'PlanoBase' 800 200 720 @(
 '- nombre_original: str',
 '- content_type: str',
 '- hash_sha256: str?',
 '- tamano_bytes: int?',
 '- ubicacion_fisica: str',
 '- expediente: str',
 '- direccion_referencia: str',
 '- parcela: str',
 '- circunscripcion: str',
 '- seccion: str',
 '- manzana: str',
 '- parcela_catastral: str',
 '- nomenclatura: str?',
 '- estado: EstadoPlano',
 '- ia_estado: EstadoIA',
 '- ia_error: str?',
 '- ia_propuesta: str?',
 '- creado_por: str?',
 '- validado_por: str?',
 '- validado_en: datetime?',
 '- activo: bool'
) @(
 '+ get_nombre_original(): str',
 '+ set_nombre_original(valor: str): void',
 '+ get_content_type(): str',
 '+ set_content_type(valor: str): void',
 '+ get_hash_sha256(): str?',
 '+ set_hash_sha256(valor: str?): void',
 '+ get_tamano_bytes(): int?',
 '+ set_tamano_bytes(valor: int?): void',
 '+ get_ubicacion_fisica(): str',
 '+ set_ubicacion_fisica(valor: str): void',
 '+ get_expediente(): str',
 '+ set_expediente(valor: str): void',
 '+ get_direccion_referencia(): str',
 '+ set_direccion_referencia(valor: str): void',
 '+ get_parcela(): str',
 '+ set_parcela(valor: str): void',
 '+ get_circunscripcion(): str',
 '+ set_circunscripcion(valor: str): void',
 '+ get_seccion(): str',
 '+ set_seccion(valor: str): void',
 '+ get_manzana(): str',
 '+ set_manzana(valor: str): void',
 '+ get_parcela_catastral(): str',
 '+ set_parcela_catastral(valor: str): void',
 '+ get_nomenclatura(): str?',
 '+ set_nomenclatura(valor: str?): void',
 '+ get_estado(): EstadoPlano',
 '+ set_estado(valor: EstadoPlano): void',
 '+ get_ia_estado(): EstadoIA',
 '+ set_ia_estado(valor: EstadoIA): void',
 '+ get_ia_error(): str?',
 '+ set_ia_error(valor: str?): void',
 '+ get_ia_propuesta(): str?',
 '+ set_ia_propuesta(valor: str?): void',
 '+ get_creado_por(): str?',
 '+ set_creado_por(valor: str?): void',
 '+ get_validado_por(): str?',
 '+ set_validado_por(valor: str?): void',
 '+ get_validado_en(): datetime?',
 '+ set_validado_en(valor: datetime?): void',
 '+ get_activo(): bool',
 '+ set_activo(valor: bool): void'
)
Box 'Plano' 1640 200 740 @(
 '- id: int?',
 '- id_inmueble: int?',
 '- minio_path: str',
 '- creado_en: datetime',
 '- actualizado_en: datetime'
) @(
 '+ get_id(): int?',
 '+ set_id(valor: int?): void',
 '+ get_id_inmueble(): int?',
 '+ set_id_inmueble(valor: int?): void',
 '+ get_minio_path(): str',
 '+ set_minio_path(valor: str): void',
 '+ get_creado_en(): datetime',
 '+ set_creado_en(valor: datetime): void',
 '+ get_actualizado_en(): datetime',
 '+ set_actualizado_en(valor: datetime): void',
 '+ get_eventos(): List<EventoAuditoria>',
 '+ set_eventos(valor: List<EventoAuditoria>): void',
 '+ get_procesamientos(): List<ProcesamientoIA>',
 '+ set_procesamientos(valor: List<ProcesamientoIA>): void'
)
Box 'EventoAuditoria' 2500 200 760 @(
 '- id: int?',
 '- plano_id: int',
 '- usuario_id: str',
 '- fecha: datetime',
 '- accion: str',
 '- motivo: str',
 '- valores_anteriores: str?',
 '- valores_nuevos: str?',
 '- ip_origen: str?'
) @(
 '+ get_id(): int?',
 '+ set_id(valor: int?): void',
 '+ get_plano_id(): int',
 '+ set_plano_id(valor: int): void',
 '+ get_usuario_id(): str',
 '+ set_usuario_id(valor: str): void',
 '+ get_fecha(): datetime',
 '+ set_fecha(valor: datetime): void',
 '+ get_accion(): str',
 '+ set_accion(valor: str): void',
 '+ get_motivo(): str',
 '+ set_motivo(valor: str): void',
 '+ get_valores_anteriores(): str?',
 '+ set_valores_anteriores(valor: str?): void',
 '+ get_valores_nuevos(): str?',
 '+ set_valores_nuevos(valor: str?): void',
 '+ get_ip_origen(): str?',
 '+ set_ip_origen(valor: str?): void'
)
Box 'ProcesamientoIA' 2500 1200 760 @(
 '- id: int?',
 '- plano_id: int',
 '- intento: int',
 '- estado: EstadoIA',
 '- error: str?',
 '- modelo_ia: str',
 '- version_prompt: str?',
 '- parametros_preprocesamiento: str?',
 '- texto_extraido_raw: str?',
 '- respuesta_json_raw: str?',
 '- duracion_ms: int?',
 '- fecha: datetime'
) @(
 '+ get_id(): int?',
 '+ set_id(valor: int?): void',
 '+ get_plano_id(): int',
 '+ set_plano_id(valor: int): void',
 '+ get_intento(): int',
 '+ set_intento(valor: int): void',
 '+ get_estado(): EstadoIA',
 '+ set_estado(valor: EstadoIA): void',
 '+ get_error(): str?',
 '+ set_error(valor: str?): void',
 '+ get_modelo_ia(): str',
 '+ set_modelo_ia(valor: str): void',
 '+ get_version_prompt(): str?',
 '+ set_version_prompt(valor: str?): void',
 '+ get_parametros_preprocesamiento(): str?',
 '+ set_parametros_preprocesamiento(valor: str?): void',
 '+ get_texto_extraido_raw(): str?',
 '+ set_texto_extraido_raw(valor: str?): void',
 '+ get_respuesta_json_raw(): str?',
 '+ set_respuesta_json_raw(valor: str?): void',
 '+ get_duracion_ms(): int?',
 '+ set_duracion_ms(valor: int?): void',
 '+ get_fecha(): datetime',
 '+ set_fecha(valor: datetime): void'
)
Inherit 800 330 690
Inherit 1640 330 1520
Line 2380 400 2500 400
Txt '1' 2390 355 $small
Txt '0..*' 2435 355 $small
Line 2010 874 2010 1400
Line 2010 1400 2500 1400
Txt '1' 2025 900 $small
Txt 'procesamientos' 2040 1350 $small
Txt '0..*' 2420 1355 $small
Box 'EstadoPlano  <<enum>>' 70 1200 620 @('pendiente','validado','sin_ubicacion')
Box 'EstadoIA  <<enum>>' 70 1500 620 @('procesando','completado','error','no_aplica')
Txt 'Encapsulamiento: atributos privados (-) y acceso exclusivo por getters/setters (+).' 70 2950 $small
Txt 'Herencia: el triángulo apunta a la clase base. Cada plano puede tener múltiples eventos e intentos de IA.' 70 3000 $small
Txt 'Basado en backend/src/models.py | Clases del dominio persistente' 70 3070 $small
$bmp.Save($dest,[System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Output $dest
