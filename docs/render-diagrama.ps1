Add-Type -AssemblyName System.Drawing
$dest = Join-Path $PWD 'docs/diagrama-clases.png'
$bmp = New-Object System.Drawing.Bitmap 2800,1575
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
$headFont = New-Object System.Drawing.Font 'Segoe UI',25,([System.Drawing.FontStyle]::Bold)
$font = New-Object System.Drawing.Font 'Consolas',20
$small = New-Object System.Drawing.Font 'Segoe UI',20
function Txt($s,$x,$y,$f=$font) { $g.DrawString($s,$f,$brush,[single]$x,[single]$y) }
function Box($name,$x,$y,$w,$rows) {
 $h = 72 + $rows.Count*40 + 20
 $g.FillRectangle($fill,$x,$y,$w,68)
 $g.DrawRectangle($pen,$x,$y,$w,$h)
 $g.DrawLine($pen,$x,($y+68),($x+$w),($y+68))
 Txt $name ($x+20) ($y+12) $headFont
 for($i=0;$i -lt $rows.Count;$i++){Txt $rows[$i] ($x+18) ($y+80+$i*40)}
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
Box 'DatosPlano' 70 220 520 @('+ texto_extraido: str?','+ arquitecto: str?','+ anio: int?','+ titulo: str?','+ ubicacion: str?','+ escala: str?','+ tipo_de_plano: str?','+ material_soporte: str?','+ notas: str?')
Box 'PlanoBase' 730 220 670 @('+ nombre_original: str','+ content_type: str','+ hash_sha256: str?','+ tamano_bytes: int?','+ ubicacion_fisica: str','+ expediente: str','+ direccion_referencia: str','+ parcela: str','+ circunscripcion: str','+ seccion: str','+ manzana: str','+ parcela_catastral: str','+ nomenclatura: str?','+ estado: EstadoPlano','+ ia_estado: EstadoIA','+ ia_error: str?','+ ia_propuesta: str?','+ creado_por: str?','+ validado_por: str?','+ validado_en: datetime?','+ activo: bool')
Box 'Plano' 1540 220 570 @('+ id: int?','+ minio_path: str','+ creado_en: datetime','+ actualizado_en: datetime')
Box 'EventoAuditoria' 2220 220 510 @('+ id: int?','+ plano_id: int','+ usuario_id: str','+ fecha: datetime','+ accion: str','+ motivo: str','+ valores_anteriores: str?','+ valores_nuevos: str?','+ ip_origen: str?')
Box 'ProcesamientoIA' 2080 830 650 @('+ id: int?','+ plano_id: int','+ intento: int','+ estado: EstadoIA','+ error: str?','+ modelo_ia: str','+ version_prompt: str?','+ parametros_preprocesamiento: str?','+ texto_extraido_raw: str?','+ respuesta_json_raw: str?','+ duracion_ms: int?','+ fecha: datetime')
Inherit 730 330 590
Inherit 1540 330 1400
Line 2110 400 2220 400
Txt '1' 2120 355 $small
Txt '0..*' 2155 355 $small
Line 1810 472 1810 950
Line 1810 950 2080 950
Txt '1' 1825 495 $small
Txt 'procesamientos' 1825 865 $small
Txt '0..*' 1995 910 $small
Box 'EstadoPlano  <<enum>>' 70 830 520 @('pendiente','validado','sin_ubicacion')
Box 'EstadoIA  <<enum>>' 70 1150 520 @('procesando','completado','error','no_aplica')
Txt 'Herencia: el triángulo apunta a la clase base.' 730 1260 $small
Txt 'Cada plano puede tener múltiples eventos e intentos de IA.' 730 1310 $small
Txt '? = opcional. Atributos heredados sin repetir.' 730 1360 $small
Txt 'Basado en backend/src/models.py | Clases del dominio persistente' 70 1500 $small
$bmp.Save($dest,[System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Output $dest
