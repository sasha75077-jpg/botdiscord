// Заглушка: весь статический фронт отдается из [assets] (SPA),
// сюда долетают только запросы без совпавшего ассета (на практике — никогда).
export default {
  async fetch(): Promise<Response> {
    return new Response('Not found', { status: 404 });
  },
};
