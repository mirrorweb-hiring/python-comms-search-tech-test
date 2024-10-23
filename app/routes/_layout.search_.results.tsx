import { type LoaderFunctionArgs, json } from '@remix-run/node'
import { Outlet, useLoaderData, useSearchParams } from '@remix-run/react'
import { requireSession } from '~/lib/auth'
import { api } from '~/lib/utils'
import { useState } from 'react'

export async function loader({ request }: LoaderFunctionArgs) {
  const { session } = await requireSession(request)

  const url = new URL(request.url)
  const query = url.searchParams.get('q') || ''

  const messages = await api(`/search?q=${query}`, {
    headers: {
      cookie: session,
    },
  })

  return json({ messages })
}

export default function SearchResults() {
  // @ts-ignore
  const { messages } = useLoaderData()
  const [searchParams] = useSearchParams()
  const [currentPage, setCurrentPage] = useState(1)
  const messagesPerPage = 10
  const numberOfPages = Math.ceil(messages.length / messagesPerPage)

  const lastIndex = currentPage * messagesPerPage
  const firstIndex = lastIndex - messagesPerPage
  const currentMessages = messages.slice(firstIndex, lastIndex)

  const setPage = (pageNumber: number) => {
    setCurrentPage(pageNumber)
  }

  return (
    <div className='py-4'>
      <main>
        <div className='mx-auto max-w-6xl py-4 px-8'>
          <div className='overflow-hidden rounded-lg bg-white shadow'>
            <div className='p-8 space-y-6'>
              <div className='space-y-1'>
                <h2 className='text-xl font-semibold leading-6 text-gray-900'>
                  Search Results
                </h2>
                <p className='text-sm text-gray-500'>
                  Showing results for:{' '}
                  <span
                    className='font-semibold text-gray-900'
                    dangerouslySetInnerHTML={{
                      __html: searchParams.get('q') || '',
                    }}
                  />
                </p>
                <p className='text-sm text-gray-500'>
                  Result count: {messages.length}
                </p>
                <p className='text-sm text-gray-500'>
                  Showing Results {firstIndex} - {lastIndex}
                </p>
              </div>

              <div className='flex space-x-4'>
                <ul
                  role='list'
                  className='w-2/5 flex-shrink-0 divide-y divide-gray-100 overflow-scroll bg-white shadow-sm ring-1 ring-gray-900/5 sm:rounded-xl'
                >
                  {messages &&
                    currentMessages.map((message: any) => {
                      return (
                        <li className='relative flex justify-between gap-x-6 px-3 py-4 hover:bg-gray-50 sm:px-6'>
                          <div className='flex min-w-0 gap-x-4'>
                            <div className='min-w-0 flex-auto'>
                              <p className='text-sm font-semibold leading-6 text-gray-900'>
                                <div>{message.from_email}</div>
                              </p>
                              <p className='mt-1 flex text-xs leading-5 text-gray-500'>
                                <span className='relative truncate'>
                                  {message.content}
                                </span>
                              </p>
                            </div>
                          </div>
                          <div className='flex shrink-0 items-center gap-x-4'>
                            <div className='hidden sm:flex sm:flex-col sm:items-end'>
                              <a
                                href={`/search/results/${
                                  message.id
                                }?q=${searchParams.get('q')}`}
                                className='text-sm font-semibold leading-6 text-pink-600 hover:underline'
                              >
                                View
                              </a>
                            </div>
                          </div>
                        </li>
                      )
                    })}
                </ul>

                <div className='h-full w-full'>
                  <Outlet />
                </div>
              </div>
              <div className='flex items-center justify-center h-full ring-1 ring-gray-900/5 rounded-xl shadow'>
                {Array(numberOfPages).fill(0).map((_, i) => (
                  <button className="w-32 h-12 px-4 py-2 text-lg rounded shadow" onClick={() => setPage(i + 1)}>
                    {i + 1}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
