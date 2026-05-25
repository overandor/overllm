import { openai } from '@ai-sdk/openai';
import { streamText } from 'ai';

export const runtime = 'edge';

export async function POST(req: Request) {
  const { prompt } = await req.json();

  const result = await streamText({
    model: openai('gpt-4o-mini'),
    prompt: `You are OverLLM, a personal-contextual AI assistant. Help the user with their request.

User: ${prompt}`,
  });

  return result.toTextStreamResponse();
}
