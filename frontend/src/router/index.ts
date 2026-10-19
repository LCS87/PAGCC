import { createRouter, createWebHistory } from 'vue-router'

import type { Role } from '@/api/types'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    description?: string
    public?: boolean
    roles?: Role[]
  }
}

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { title: 'Entrar', public: true },
    },
    {
      path: '/',
      component: () => import('@/layouts/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'overview',
          component: () => import('@/views/OverviewView.vue'),
          meta: { title: 'Visão geral' },
        },
        {
          path: 'agenda',
          name: 'agenda',
          component: () => import('@/views/AgendaView.vue'),
          meta: { title: 'Agenda e operação' },
        },
        {
          path: 'profissionais',
          name: 'professionals',
          component: () => import('@/views/ProfessionalsView.vue'),
          meta: { title: 'Profissionais e unidades' },
        },
        {
          path: 'profissionais/:id',
          name: 'professional-detail',
          component: () => import('@/views/ProfessionalDetailView.vue'),
          meta: { title: 'Detalhe do profissional' },
        },
        {
          path: 'atendimentos',
          name: 'attendances',
          component: () => import('@/views/AttendancesView.vue'),
          meta: { title: 'Atendimentos' },
        },
        {
          path: 'atendimentos/:id',
          name: 'attendance-detail',
          component: () => import('@/views/AttendanceDetailView.vue'),
          meta: { title: 'Detalhe do atendimento' },
        },
        {
          path: 'analytics',
          name: 'analytics',
          component: () => import('@/views/AnalyticsView.vue'),
          meta: { title: 'Analytics' },
        },
        {
          path: 'qualidade',
          name: 'quality',
          component: () => import('@/views/DataQualityView.vue'),
          meta: { title: 'Qualidade dos dados' },
        },
        {
          path: 'admin',
          name: 'admin',
          component: () => import('@/views/AdminView.vue'),
          meta: { title: 'Administração', roles: ['ADMIN', 'GESTOR'] },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { title: 'Página não encontrada', public: true },
    },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (!to.meta.public && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'overview' }
  }

  if (to.meta.roles && !auth.hasRole(...to.meta.roles)) {
    return { name: 'overview' }
  }

  return true
})

router.afterEach((to) => {
  const title = to.meta.title ? `${to.meta.title} · Clinic Analytics` : 'Clinic Analytics'
  document.title = title
})

export default router
