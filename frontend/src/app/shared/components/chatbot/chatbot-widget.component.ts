import { Component, ElementRef, HostListener, inject, signal, viewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FpIconsModule } from '../../icons/fp-icons.module';
import { ChatbotService } from '../../../core/services/chatbot.service';

interface SuggestedQuestion {
  label: string;
  query: string;
}

interface ChatMessage {
  id: number;
  role: 'bot' | 'user';
  text: string;
  sources?: string[];
}

const CHATBOT_GREETING =
  "Hi! I'm the FraudPulse assistant. Ask me about how the system scores payments, the tech stack, or how to get access.";

const CHATBOT_ERROR =
  "Sorry — I couldn't reach the assistant just now. Please try again in a moment, or use the Request access form to contact the team.";

const SUGGESTED_QUESTIONS: SuggestedQuestion[] = [
  { label: 'What is FraudPulse?', query: 'What is FraudPulse?' },
  { label: 'How does scoring work?', query: 'How does scoring work?' },
  { label: 'What is the tech stack?', query: 'What is the tech stack?' },
  { label: 'How do I get access?', query: 'How do I get access?' },
];

@Component({
  selector: 'app-chatbot-widget',
  standalone: true,
  imports: [FormsModule, FpIconsModule],
  templateUrl: './chatbot-widget.component.html',
  styleUrl: './chatbot-widget.component.css',
})
export class ChatbotWidgetComponent {
  private readonly chatbot = inject(ChatbotService);

  readonly open = signal(false);
  readonly draft = signal('');
  readonly typing = signal(false);
  readonly messages = signal<ChatMessage[]>([
    { id: 0, role: 'bot', text: CHATBOT_GREETING },
  ]);

  readonly suggestions = SUGGESTED_QUESTIONS;

  private readonly scrollRegion = viewChild<ElementRef<HTMLElement>>('scrollRegion');
  private seq = 0;

  toggle(): void {
    this.open.update((value) => !value);
  }

  close(): void {
    this.open.set(false);
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.close();
  }

  send(): void {
    const text = this.draft().trim();
    if (!text || this.typing()) return;
    this.draft.set('');
    this.ask(text);
  }

  clear(): void {
    this.seq = 0;
    this.draft.set('');
    this.typing.set(false);
    this.messages.set([{ id: 0, role: 'bot', text: CHATBOT_GREETING }]);
  }

  get canClear(): boolean {
    return this.messages().length > 1 || this.typing();
  }

  askSuggestion(query: string, label: string): void {
    if (this.typing()) return;
    this.ask(query, label);
  }

  private ask(query: string, displayText?: string): void {
    this.pushMessage('user', displayText ?? query);
    this.typing.set(true);
    this.scrollToBottom();

    this.chatbot.ask(query).subscribe({
      next: (res) => {
        this.typing.set(false);
        const sources = res.refused
          ? undefined
          : [...new Set(res.sources.map((s) => s.title))];
        this.pushMessage('bot', res.answer, sources);
      },
      error: () => {
        this.typing.set(false);
        this.pushMessage('bot', CHATBOT_ERROR);
      },
    });
  }

  private pushMessage(role: ChatMessage['role'], text: string, sources?: string[]): void {
    this.seq += 1;
    this.messages.update((list) => [...list, { id: this.seq, role, text, sources }]);
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      const el = this.scrollRegion()?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }
}
