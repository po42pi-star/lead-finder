// Сквозной тест: «робот-пользователь» проходит основной сценарий в установленном Google Chrome.
// Запуск при работающем ./start.sh:  npm run test:e2e
import assert from "node:assert/strict";
import { chromium } from "playwright-core";

const BASE_URL = process.env.BASE_URL ?? "http://localhost:5173";
const browser = await chromium.launch({ channel: "chrome", headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));

async function step(name, fn) {
  const started = Date.now();
  await fn();
  console.log(`✓ ${name} (${((Date.now() - started) / 1000).toFixed(1)} c)`);
}

try {
  await step("главная открывается, сервер на связи", async () => {
    await page.goto(BASE_URL);
    await page.getByText("Пилотная версия").waitFor();
  });

  await step("поиск по готовому сценарию находит компании", async () => {
    await page.getByRole("button", { name: "Монтажники вентиляции, Самара" }).click();
    await page.locator("article").first().waitFor({ timeout: 60_000 });
    assert.ok((await page.locator("article").count()) > 0);
  });

  await step("раскрывается расшифровка скоринга", async () => {
    await page.getByText(/Почему \d+ баллов/).first().click();
    await page.getByText(/Источники:/).first().waitFor();
  });

  await step("аналитика по двум выбранным компаниям", async () => {
    await page.getByRole("checkbox").nth(0).check();
    await page.getByRole("checkbox").nth(1).check();
    await page.getByRole("button", { name: "Аналитика по выбранным" }).click();
    await page.getByText("Вопросы для звонка").waitFor({ timeout: 60_000 });
    await page.getByText("Контакты и ЛПР").waitFor();
  });

  await step("ассистент отвечает с учётом выбранной компании", async () => {
    await page.getByRole("button", { name: "Спросить ассистента" }).first().click();
    await page.getByText(/Контекст:/).waitFor();
    await page.getByRole("textbox").fill("Какие вентиляторы предложить этому клиенту?");
    await page.keyboard.press("Enter");
    await page.locator('button[aria-label="Полезный ответ"]').waitFor({ timeout: 90_000 });
    assert.equal(await page.getByText("Ассистент недоступен").count(), 0);
  });

  assert.deepEqual(errors, [], `Ошибки JavaScript на странице: ${errors.join("; ")}`);
  console.log("\nВсе шаги пройдены");
} finally {
  await browser.close();
}
