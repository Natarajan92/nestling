export async function cardImage(title: string, lines: string[], footer: string): Promise<Blob> {
  await document.fonts.ready;
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1350;
  const context = canvas.getContext("2d");

  if (!context)
    throw new Error("Images are unavailable in this browser.");

  const ctx: CanvasRenderingContext2D = context;
  const styles = getComputedStyle(document.documentElement);
  const display = styles.getPropertyValue("--font-fraunces").trim() || "Georgia";
  const body = styles.getPropertyValue("--font-inter").trim() || "Arial";

  function wrap(text: string, size: number, family: string): string[] {
    ctx.font = `${size}px ${family}`;
    const output: string[] = [];

    for (const paragraph of text.split("\n")) {
      let line = "";

      for (const word of paragraph.split(" ")) {
        if (ctx.measureText(`${line} ${word}`.trim()).width > 880 && line) {
          output.push(line);
          line = "";
        }

        // URLs and unusually long names also wrap inside a word.
        for (const char of (line ? " " : "") + word) {
          if (ctx.measureText(line + char).width > 880 && line) {
            output.push(line);
            line = "";
          }

          line += char;
        }
      }

      output.push(line);
    }

    return output;
  }

  const titleLines = wrap(title, 60, display);
  const footerLines = wrap(footer, 23, body);
  const bodyLines = lines.flatMap(line => [...wrap(line, 34, body), ""]);
  const needed = 180 + titleLines.length * 80 + 50 + bodyLines.length * 51 + 60 + footerLines.length * 34.5 + 150;
  canvas.height = Math.max(1350, Math.ceil(needed));
  ctx.fillStyle = "#FFF8F1";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#F7B49A";
  ctx.beginPath();
  ctx.ellipse(920, 100, 280, 220, 0, 0, Math.PI * 2);
  ctx.fill();
  let y = 180;

  function draw(content: string[], size: number, family: string, lineHeight: number) {
    ctx.font = `${size}px ${family}`;

    for (const line of content) {
      ctx.fillText(line, 100, y);
      y += lineHeight;
    }
  }

  ctx.fillStyle = "#2E2A3A";
  draw(titleLines, 60, display, 80);
  y += 50;
  draw(bodyLines, 34, body, 51);
  y = Math.max(y + 60, canvas.height - 150 - footerLines.length * 34.5);
  ctx.fillStyle = "#6B6577";
  draw(footerLines, 23, body, 34.5);
  ctx.fillStyle = "#2E2A3A";
  ctx.font = `32px ${display}`;
  ctx.fillText("Nestling · From bump to baby", 100, canvas.height - 70);

  return new Promise(
    (resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("Could not create image")), "image/png")
  );
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
