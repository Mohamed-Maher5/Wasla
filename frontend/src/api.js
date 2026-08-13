// This file is the single bridge between the Wasla frontend and backend data layer.
// Every screen uses it to request platform data instead of reaching into transport details.

const MIN_DELAY_MS = 200;
const MAX_DELAY_MS = 1000;

const departments = [
  { id: 1, name: "خدمة العملاء", description: "متابعة الشكاوى العامة وتجربة العملاء" },
  { id: 2, name: "الموارد البشرية", description: "طلبات الموظفين والاستفسارات الداخلية" },
  { id: 3, name: "المالية", description: "الفواتير والمدفوعات والمراجعات المالية" },
];

let tickets = [
  {
    id: 1,
    customer_name: "أحمد محمود",
    status: "unresolved",
    department_id: 1,
    assigned_agent_id: 101,
    customer_phone: "+201001112233",
    problem_description: "العميل بيقول إن الطلب اتأخر ومحتاج يعرف ميعاد التسليم النهائي.",
    created_at: "2026-08-12T10:15:00.000Z",
  },
  {
    id: 2,
    customer_name: "منى حسن",
    status: "resolved",
    department_id: 3,
    assigned_agent_id: 102,
    customer_phone: "+201221234567",
    problem_description: "تم خصم مبلغ مرتين من البطاقة والعميلة محتاجة تأكيد رد المبلغ.",
    created_at: "2026-08-11T14:30:00.000Z",
  },
  {
    id: 3,
    customer_name: "كريم سمير",
    status: "unresolved",
    department_id: 2,
    assigned_agent_id: 103,
    customer_phone: "+201155667788",
    problem_description: "استفسار عن حالة طلب إجازة لم يظهر في النظام.",
    created_at: "2026-08-13T08:45:00.000Z",
  },
];

function delay() {
  const duration =
    Math.floor(Math.random() * (MAX_DELAY_MS - MIN_DELAY_MS + 1)) + MIN_DELAY_MS;

  return new Promise((resolve) => {
    setTimeout(resolve, duration);
  });
}

async function respond(value) {
  await delay();
  return typeof value === "function" ? value() : value;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function nextTicketId() {
  return tickets.reduce((maxId, ticket) => Math.max(maxId, ticket.id), 0) + 1;
}

export async function login(credentials) {
  return respond(() => ({
    access_token: `mock-token-${credentials?.email || credentials?.username || "user"}`,
    token_type: "bearer",
  }));
}

export async function getTickets() {
  return respond(() => clone(tickets));
}

export async function getTicket(id) {
  return respond(() => {
    const ticket = tickets.find((item) => item.id === Number(id));
    if (!ticket) {
      throw new Error("Ticket not found");
    }
    return clone(ticket);
  });
}

export async function createTicket(data) {
  return respond(() => {
    const ticket = {
      id: nextTicketId(),
      customer_name: data.customer_name,
      status: "unresolved",
      department_id: data.department_id,
      assigned_agent_id: data.assigned_agent_id ?? null,
      customer_phone: data.customer_phone,
      problem_description: data.problem_description,
      created_at: new Date().toISOString(),
    };

    tickets = [ticket, ...tickets];
    return clone(ticket);
  });
}

export async function callCustomer(ticketId) {
  return respond(() => {
    const ticket = tickets.find((item) => item.id === Number(ticketId));
    if (!ticket) {
      throw new Error("Ticket not found");
    }

    return {
      success: true,
      outcome:
        ticket.status === "resolved"
          ? "العميل أكد إن المشكلة اتحلت وشكر فريق الدعم."
          : "العميل قال إن المشكلة لسه موجودة ومحتاج متابعة من الموظف.",
    };
  });
}

export async function resolveTicket(ticketId) {
  return respond(() => {
    const ticket = tickets.find((item) => item.id === Number(ticketId));
    if (!ticket) {
      throw new Error("Ticket not found");
    }

    ticket.status = "resolved";
    return { id: ticket.id, status: "resolved" };
  });
}

export async function unresolveTicket(ticketId) {
  return respond(() => {
    const ticket = tickets.find((item) => item.id === Number(ticketId));
    if (!ticket) {
      throw new Error("Ticket not found");
    }

    ticket.status = "unresolved";
    return { id: ticket.id, status: "unresolved" };
  });
}

export async function askChatbot(question) {
  return respond(() => ({
    answer: `حسب مستندات القسم، نقدر نبدأ بمتابعة السؤال ده: "${question}". لو محتاج تفاصيل أكتر، ابعت رقم التذكرة أو اسم العميل.`,
  }));
}

export async function getDepartments() {
  return respond(() => clone(departments));
}

export async function uploadDocument(file) {
  return respond(() => ({
    success: true,
    filename: file?.name || "document.pdf",
  }));
}
