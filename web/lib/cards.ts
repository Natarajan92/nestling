export async function cardImage(title: string, lines: string[], footer: string): Promise<Blob> {
  await document.fonts.ready;
  const canvas = document.createElement("canvas"); canvas.width = 1080; canvas.height = 1350;
  const context = canvas.getContext("2d"); if (!context) throw new Error("Images are unavailable in this browser.");
  const ctx: CanvasRenderingContext2D = context;
  ctx.fillStyle = "#FFF8F1"; ctx.fillRect(0, 0, 1080, 1350);
  ctx.fillStyle = "#F7B49A"; ctx.beginPath(); ctx.ellipse(920, 100, 280, 220, 0, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = "#2E2A3A"; ctx.font = "600 60px var(--font-fraunces), Georgia";
  let y = 180;
  function wrap(text: string, size: number, family: string) {
    ctx.font = `${size}px ${family}`;
    for (const paragraph of text.split("\n")) {
      let line = "";
      for (const word of paragraph.split(" ")) { const next = line ? `${line} ${word}` : word; if (ctx.measureText(next).width > 880 && line) { ctx.fillText(line, 100, y); y += size * 1.5; line = word; } else line = next; }
      ctx.fillText(line, 100, y); y += size * 1.5;
    }
  }
  wrap(title, 60, "Georgia"); y += 50;
  for (const line of lines) { wrap(line, 34, "Arial"); y += 24; }
  ctx.fillStyle = "#6B6577"; y = Math.max(y + 30, 1080); wrap(footer, 23, "Arial");
  ctx.fillStyle = "#2E2A3A"; ctx.font = "32px Georgia"; ctx.fillText("Nestling · From bump to baby", 100, 1270);
  return new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("Could not create image")), "image/png"));
}
export function downloadBlob(blob: Blob, filename: string) { const url = URL.createObjectURL(blob); const a = document.createElement("a"); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
